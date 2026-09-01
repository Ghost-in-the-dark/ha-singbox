"""Data coordinator for the sing-box integration.

Unlike a polling coordinator, sing-box pushes data: SubscribeStatus streams a
Status message roughly every second, SubscribeGroups pushes on every change.
The coordinator keeps both streams alive, reconnects with exponential backoff
on failure and exposes the latest snapshot to the entities.
"""

from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
        client: SingBoxClient,
        update_interval_seconds: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=None, config_entry=entry
        )
        self.client = client
        self.data = SingBoxStatus()
        self._stream_tasks: list[asyncio.Task] = []
        self.clash_mode_available = False
        self._groups_ready = asyncio.Event()
        # SubscribeStatus interval is a Go time.Duration, i.e. nanoseconds.
        self._interval_seconds = update_interval_seconds
        self._interval_ns = update_interval_seconds * 1_000_000_000

    async def async_setup(self) -> None:
        """Fetch static info and start the push streams."""
        try:
            version, api_version = await self.client.get_version()
            self.data.version = version
            self.data.api_version = api_version
            self.data.started_at = await self.client.get_started_at()
        except GrpcError as err:
            raise err
        except (asyncio.TimeoutError, OSError, ConnectionError) as err:
            raise ConnectionError(f"cannot reach sing-box API: {err}") from err

        try:
            mode_list, current = await self.client.get_clash_mode_status()
            self.data.clash_mode_list = mode_list
            self.data.clash_mode = current
            self.clash_mode_available = True
        except GrpcError as err:
            if err.status != GRPC_STATUS_NOT_FOUND:
                _LOGGER.warning("clash mode unavailable: %s", err)
            self.clash_mode_available = False

        self._stream_tasks = [
            asyncio.create_task(self._run_status_stream()),
            asyncio.create_task(self._run_groups_stream()),
        ]
        # Entities for outbound groups are created at platform setup, so wait
        # for the first Groups push before proceeding.
        try:
            await asyncio.wait_for(self._groups_ready.wait(), timeout=10)
        except asyncio.TimeoutError:
            _LOGGER.warning("no groups received from sing-box within 10s")

    async def async_shutdown(self) -> None:
        """Cancel the push streams."""
        for task in self._stream_tasks:
            task.cancel()
        await asyncio.gather(*self._stream_tasks, return_exceptions=True)
        self._stream_tasks.clear()
        await self.client.close()

    # -- streams ------------------------------------------------------------

    async def _run_status_stream(self) -> None:
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

    async def set_clash_mode(self, mode: str) -> None:
        await self.client.set_clash_mode(mode)
        self.data.clash_mode = mode
        self.async_set_updated_data(self.data)

    async def set_group_expand(self, group_tag: str, is_expand: bool) -> None:
        await self.client.set_group_expand(group_tag, is_expand)

    async def url_test(self, outbound_tag: str) -> None:
        await self.client.url_test(outbound_tag)

    async def close_connection(self, connection_id: str) -> None:
        await self.client.close_connection(connection_id)

    async def close_all_connections(self) -> None:
        await self.client.close_all_connections()

    def group(self, tag: str) -> SingBoxGroup | None:
        return next((g for g in self.data.groups if g.tag == tag), None)
