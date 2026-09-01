"""Data coordinator for the sing-box integration.

sing-box pushes data over its gRPC ``api`` service (SubscribeStatus /
SubscribeGroups streams); on versions without that service (clash_api only)
the same data is gathered from the Clash REST/WebSocket API. The coordinator
keeps the backend streams alive, reconnects with exponential backoff on
failure and exposes the latest snapshot to the entities.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .backend import BACKEND_CLASH, BACKEND_GRPC
from .clash import ClashApiError, ClashClient, POLL_INTERVAL_SECONDS
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from .grpc import (
    GRPC_STATUS_NOT_FOUND,
    GRPC_STATUS_UNAUTHENTICATED,
    GrpcError,
    SingBoxClient,
    SingBoxGroup,
    SingBoxStatus,
    _bool,
    _int,
    flatten_proxies,
)

_LOGGER = logging.getLogger(__package__)

_MIN_BACKOFF = 5.0
_MAX_BACKOFF = 60.0


class SingBoxCoordinator(DataUpdateCoordinator[SingBoxStatus]):
    """Manages the sing-box API connection and its push streams."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SingBoxClient | ClashClient,
        backend: str,
        update_interval_seconds: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=None, config_entry=entry
        )
        self.client = client
        self.backend = backend
        self.data = SingBoxStatus()
        self._stream_tasks: list[asyncio.Task] = []
        self.clash_mode_available = False
        self._groups_ready = asyncio.Event()
        # SubscribeStatus interval is a Go time.Duration, i.e. nanoseconds.
        self._interval_seconds = update_interval_seconds
        self._interval_ns = update_interval_seconds * 1_000_000_000

    async def async_setup(self) -> None:
        """Fetch static info and start the backend streams."""
        if self.backend == BACKEND_GRPC:
            await self._setup_grpc()
        else:
            await self._setup_clash()
        # Entities for outbound groups are created at platform setup, so wait
        # for the first groups snapshot before proceeding.
        try:
            await asyncio.wait_for(self._groups_ready.wait(), timeout=10)
        except asyncio.TimeoutError:
            _LOGGER.warning("no groups received from sing-box within 10s")

    async def _setup_grpc(self) -> None:
        client: SingBoxClient = self.client
        try:
            version, api_version = await client.get_version()
            self.data.version = version
            self.data.api_version = api_version
            self.data.started_at = await client.get_started_at()
        except (asyncio.TimeoutError, OSError, ConnectionError) as err:
            raise ConnectionError(f"cannot reach sing-box API: {err}") from err

        try:
            mode_list, current = await client.get_clash_mode_status()
            self.data.clash_mode_list = mode_list
            self.data.clash_mode = current
            self.clash_mode_available = True
        except GrpcError as err:
            if err.status != GRPC_STATUS_NOT_FOUND:
                _LOGGER.warning("clash mode unavailable: %s", err)
            self.clash_mode_available = False

        self._stream_tasks = [
            asyncio.create_task(self._run_grpc_status_stream()),
            asyncio.create_task(self._run_groups_stream()),
        ]

    async def _setup_clash(self) -> None:
        client: ClashClient = self.client
        try:
            self.data.version = await client.get_version()
        except (asyncio.TimeoutError, OSError, ConnectionError) as err:
            raise ConnectionError(f"cannot reach sing-box API: {err}") from err

        try:
            mode_list, current = await client.get_configs()
            self.data.clash_mode_list = mode_list
            self.data.clash_mode = current
            self.clash_mode_available = True
        except ClashApiError as err:
            _LOGGER.warning("clash mode unavailable: %s", err)
            self.clash_mode_available = False

        self._stream_tasks = [
            asyncio.create_task(self._run_clash_traffic_stream()),
            asyncio.create_task(self._run_clash_poll_loop()),
        ]

    async def async_shutdown(self) -> None:
        """Cancel the backend streams."""
        for task in self._stream_tasks:
            task.cancel()
        await asyncio.gather(*self._stream_tasks, return_exceptions=True)
        self._stream_tasks.clear()
        await self.client.close()

    # -- streams ------------------------------------------------------------

    async def _run_grpc_status_stream(self) -> None:
        backoff = _MIN_BACKOFF
        while True:
            try:
                async for fields in self.client.subscribe_status(self._interval_ns):
                    self._apply_status(fields)
                    backoff = _MIN_BACKOFF
                    self._mark_available()
            except asyncio.CancelledError:
                raise
            except GrpcError as err:
                _LOGGER.error("status stream failed: %s", err)
                if err.status == GRPC_STATUS_UNAUTHENTICATED:
                    self._mark_unavailable(err)
                    return
            except (asyncio.TimeoutError, OSError, ConnectionError) as err:
                _LOGGER.warning("status stream lost: %s", err)
            self._mark_unavailable(None)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _run_groups_stream(self) -> None:
        backoff = _MIN_BACKOFF
        while True:
            try:
                async for groups in self.client.subscribe_groups():
                    self.data.groups = groups
                    self.data.proxies = flatten_proxies(groups)
                    self._groups_ready.set()
                    backoff = _MIN_BACKOFF
                    self._mark_available()
            except asyncio.CancelledError:
                raise
            except GrpcError as err:
                _LOGGER.error("groups stream failed: %s", err)
                if err.status == GRPC_STATUS_UNAUTHENTICATED:
                    self._mark_unavailable(err)
                    return
            except (asyncio.TimeoutError, OSError, ConnectionError) as err:
                _LOGGER.warning("groups stream lost: %s", err)
            self._mark_unavailable(None)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _run_clash_traffic_stream(self) -> None:
        backoff = _MIN_BACKOFF
        while True:
            try:
                async for up, down in self.client.traffic_stream():
                    self.data.uplink = up
                    self.data.downlink = down
                    backoff = _MIN_BACKOFF
                    self._mark_available()
            except asyncio.CancelledError:
                raise
            except (ClashApiError, asyncio.TimeoutError, OSError, ConnectionError) as err:
                _LOGGER.error("traffic stream failed: %s", err)
            except (ValueError, TypeError) as err:
                _LOGGER.error("traffic stream returned a malformed frame: %s", err)
            except Exception as err:  # noqa: BLE001 - keep the stream alive
                _LOGGER.exception("traffic stream crashed: %s", err)
            self._mark_unavailable(None)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _run_clash_poll_loop(self) -> None:
        backoff = _MIN_BACKOFF
        interval = max(self._interval_seconds, POLL_INTERVAL_SECONDS)
        while True:
            try:
                groups, proxies = await self.client.get_proxies()
                self.data.groups = groups
                self.data.proxies = proxies
                self._groups_ready.set()
                await self._apply_clash_mode()
                await self._apply_clash_connections()
                backoff = _MIN_BACKOFF
                self._mark_available()
            except asyncio.CancelledError:
                raise
            except (ClashApiError, asyncio.TimeoutError, OSError, ConnectionError) as err:
                _LOGGER.warning("clash poll failed: %s", err)
                self._mark_unavailable(None)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue
            except (ValueError, TypeError) as err:
                _LOGGER.error("clash poll returned a malformed response: %s", err)
                self._mark_unavailable(None)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue
            except Exception as err:  # noqa: BLE001 - keep the loop alive
                _LOGGER.exception("clash poll loop crashed: %s", err)
                self._mark_unavailable(None)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue
            await asyncio.sleep(interval)

    async def _apply_clash_mode(self) -> None:
        try:
            mode_list, current = await self.client.get_configs()
        except (ClashApiError, asyncio.TimeoutError, OSError, ConnectionError) as err:
            _LOGGER.warning("clash mode poll failed: %s", err)
            return
        self.data.clash_mode_list = mode_list
        self.data.clash_mode = current
        self.clash_mode_available = True

    async def _apply_clash_connections(self) -> None:
        try:
            n, memory, upload_total, download_total = await self.client.get_connections()
        except (ClashApiError, asyncio.TimeoutError, OSError, ConnectionError) as err:
            _LOGGER.warning("clash connections snapshot failed: %s", err)
            return
        self.data.connections_in = n
        self.data.memory = memory
        self.data.uplink_total = upload_total
        self.data.downlink_total = download_total

    def _mark_available(self) -> None:
        if not self.last_update_success:
            self.last_update_success = True
        self.async_set_updated_data(self.data)

    def _mark_unavailable(self, err: Exception | None) -> None:
        if self.last_update_success:
            _LOGGER.warning("sing-box became unavailable%s", f": {err}" if err else "")
        self.last_update_success = False
        self.async_update_listeners()

    # -- control helpers (called by services/entities) ----------------------

    async def select_outbound(self, group_tag: str, outbound_tag: str) -> None:
        await self.client.select_outbound(group_tag, outbound_tag)

    async def set_group_expand(self, group_tag: str, is_expand: bool) -> None:
        if self.backend == BACKEND_GRPC:
            await self.client.set_group_expand(group_tag, is_expand)
            return
        raise ClashApiError(
            0, "set_group_expand is not supported by the clash API"
        )

    async def url_test(self, outbound_tag: str, url: str | None = None) -> None:
        await self.client.url_test(outbound_tag, url)

    async def close_connection(self, connection_id: str) -> None:
        await self.client.close_connection(connection_id)

    async def close_all_connections(self) -> None:
        await self.client.close_all_connections()

    async def set_clash_mode(self, mode: str) -> None:
        await self.client.set_clash_mode(mode)
        self.data.clash_mode = mode
        self.async_set_updated_data(self.data)

    def group(self, tag: str) -> SingBoxGroup | None:
        return next((g for g in self.data.groups if g.tag == tag), None)

    def _apply_status(self, fields: dict[int, list[int | bytes]]) -> None:
        self.data.memory = _int(fields, 1)
        self.data.goroutines = _int(fields, 2)
        self.data.connections_in = _int(fields, 3)
        self.data.connections_out = _int(fields, 4)
        self.data.traffic_available = _bool(fields, 5)
        # uplink/downlink are byte deltas since the previous frame; dividing by
        # the frame interval yields bytes per second.
        self.data.uplink = _int(fields, 6) / self._interval_seconds
        self.data.downlink = _int(fields, 7) / self._interval_seconds
        self.data.uplink_total = _int(fields, 8)
        self.data.downlink_total = _int(fields, 9)
