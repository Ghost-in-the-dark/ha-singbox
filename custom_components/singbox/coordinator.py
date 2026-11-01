"""Data coordinator for the sing-box integration.

sing-box pushes data over its gRPC ``api`` service (SubscribeStatus /
SubscribeGroups streams); on versions without that service (clash_api only)
the same data is gathered from the Clash REST/WebSocket API. The coordinator
keeps the backend streams alive, reconnects with exponential backoff on
failure, supervises the stream tasks and exposes the latest snapshot to the
entities.

State pushes are throttled (``_PUSH_MIN_INTERVAL``): backend frames arrive every
second, but forwarding each of them through Home Assistant floods the state
machine and the recorder.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .backend import BACKEND_GRPC
from .clash import POLL_INTERVAL_SECONDS, ClashApiError, ClashClient, is_auth_error
from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from .errors import SingBoxAuthError, SingBoxNotSupported
from .grpc import (
    GRPC_STATUS_NOT_FOUND,
    GRPC_STATUS_UNIMPLEMENTED,
    GrpcError,
    SingBoxClient,
    SingBoxConnection,
    SingBoxConnectionUpdate,
    SingBoxGroup,
    SingBoxGroupItem,
    SingBoxStatus,
    _bool,
    _int,
    flatten_proxies,
)

_LOGGER = logging.getLogger(__package__)

_MIN_BACKOFF = 5.0
_MAX_BACKOFF = 60.0
_POLL_TIMEOUT = 15.0

# Minimum time between coordinator -> entity state pushes.
_PUSH_MIN_INTERVAL = 5.0

# Guards against a division blow-up when two status frames arrive back to
# back (e.g. a reconnect delivering a frame immediately after the previous
# one) while still keeping the rate meaningful.
_MIN_RATE_WINDOW = 0.5


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
        # The update interval is not a push interval: the stream frames drive
        # the data, and this only paces the health poll that also supervises
        # the stream tasks (and is the sole source of data on a backend whose
        # streams stay down).
        poll_interval = max(
            float(update_interval_seconds), _PUSH_MIN_INTERVAL, POLL_INTERVAL_SECONDS
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
            config_entry=entry,
        )
        self.client = client
        self.backend = backend
        self.data = SingBoxStatus()
        self._stream_factories: list = []
        self._stream_tasks: list[asyncio.Task] = []
        self._push_interval = max(float(update_interval_seconds), _PUSH_MIN_INTERVAL)
        self._last_push_ts = 0.0
        self.clash_mode_available = False
        self._groups_ready = asyncio.Event()
        self._shutdown = asyncio.Event()
        # SubscribeStatus interval is a Go time.Duration, i.e. nanoseconds.
        self._interval_seconds = update_interval_seconds
        self._interval_ns = update_interval_seconds * 1_000_000_000
        # The connection list is a per-second view ("what is open right now"),
        # so it is pushed at a fixed 1 s cadence regardless of the configured
        # sensor interval. The server clamps anything below that by itself;
        # asking for it explicitly keeps the card's list fresh.
        self._connections_interval_ns = 1_000_000_000
        # Traffic is accumulated between pushes so the reported speed is the
        # average over the real elapsed time, not a single 1s frame.
        self._rate_window_start = time.monotonic()
        self._rate_up_bytes = 0
        self._rate_down_bytes = 0
        self._discovery_listeners: list = []
        # Tag -> object indexes, rebuilt on every groups snapshot: looking a
        # proxy up by tag used to be a linear scan per sensor per push.
        self._groups_index: dict[str, SingBoxGroup] = {}
        self._proxies_index: dict[str, SingBoxGroupItem] = {}
        # Live connections, keyed by their sing-box id. The clash backend
        # replaces the whole set on every poll, the gRPC backend applies the
        # deltas of the SubscribeConnections stream.
        self._connections: dict[str, SingBoxConnection] = {}
        # False as soon as the backend says it cannot list connections at
        # all (UNIMPLEMENTED / NOT_FOUND), so the websocket API can report
        # "not supported" instead of an empty list.
        self._connections_supported = True

    # -- lifecycle ----------------------------------------------------------

    async def async_setup(self) -> None:
        """Fetch static info and start the backend streams."""
        if self.backend == BACKEND_GRPC:
            await self._setup_grpc()
        else:
            await self._setup_clash()
        # The groups snapshot only arrives through a stream, so the streams
        # must be running before waiting for it.
        self._start_streams()
        # Entities for outbound groups are created at platform setup, so wait
        # for the first groups snapshot before proceeding.
        try:
            await asyncio.wait_for(self._groups_ready.wait(), timeout=10)
        except TimeoutError:
            _LOGGER.warning("no groups received from sing-box within 10s")

    async def _setup_grpc(self) -> None:
        client: SingBoxClient = self.client
        try:
            version, api_version = await client.get_version()
            self.data.version = version
            self.data.api_version = api_version
            self.data.started_at = await client.get_started_at()
        except (TimeoutError, OSError, ConnectionError) as err:
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

        self._stream_factories = [
            self._run_grpc_status_stream,
            self._run_groups_stream,
            self._run_connections_stream,
        ]

    async def _setup_clash(self) -> None:
        client: ClashClient = self.client
        try:
            self.data.version = await client.get_version()
        except (TimeoutError, OSError, ConnectionError) as err:
            raise ConnectionError(f"cannot reach sing-box API: {err}") from err

        try:
            mode_list, current = await client.get_configs()
            self.data.clash_mode_list = mode_list
            self.data.clash_mode = current
            self.clash_mode_available = True
        except ClashApiError as err:
            _LOGGER.warning("clash mode unavailable: %s", err)
            self.clash_mode_available = False

        self._stream_factories = [
            self._run_clash_traffic_stream,
            self._run_clash_poll_loop,
        ]

    async def async_shutdown(self) -> None:
        """Cancel the backend streams and close the API session."""
        self._shutdown.set()
        if self._stream_tasks:
            for task in self._stream_tasks:
                task.cancel()
            # Bounded: a wedged task must not stall the config-entry unload
            # (and with it the whole HA shutdown) for another minute.
            done, pending = await asyncio.wait(self._stream_tasks, timeout=5)
            if pending:
                _LOGGER.warning("sing-box stream tasks ignored cancellation")
            self._stream_tasks.clear()
        await self.client.close()

    def _start_streams(self) -> None:
        if not self._stream_factories:
            return
        self._stream_tasks = [asyncio.create_task(factory()) for factory in self._stream_factories]

    # -- discovery ----------------------------------------------------------

    @callback
    def async_add_discovery_listener(self, update_callback) -> None:
        """Register a callback for new groups / proxies appearing upstream."""
        self._discovery_listeners.append(update_callback)

    @callback
    def async_remove_discovery_listener(self, update_callback) -> None:
        """Remove a discovery callback."""
        self._discovery_listeners.remove(update_callback)

    @callback
    def _notify_discovery(self) -> None:
        for update_callback in list(self._discovery_listeners):
            update_callback()

    # -- DataUpdateCoordinator ----------------------------------------------

    async def _async_update_data(self) -> SingBoxStatus:
        """Health poll: refresh the snapshot and supervise the stream tasks.

        Streams deliver the data on the gRPC backend; this poll keeps the entry
        honest when a stream is wedged (a stream task that died silently left
        the sensors frozen and *available*), and is the only source of data on
        the clash backend when its WebSocket is unreachable.
        """
        self._supervise_stream_tasks()
        try:
            if self.backend == BACKEND_GRPC:
                await asyncio.wait_for(self._poll_grpc(), timeout=_POLL_TIMEOUT)
            else:
                await asyncio.wait_for(self._poll_clash(), timeout=_POLL_TIMEOUT)
        except asyncio.CancelledError:
            raise
        except (SingBoxAuthError, ClashApiError, GrpcError) as err:
            if is_auth_error(err):
                self._mark_unavailable(err)
                raise UpdateFailed(f"authentication failed: {err}") from err
            self._mark_unavailable(err)
            raise UpdateFailed(f"sing-box API error: {err}") from err
        except (TimeoutError, OSError, ConnectionError) as err:
            self._mark_unavailable(err)
            raise UpdateFailed(f"cannot reach sing-box API: {err}") from err
        except Exception as err:  # noqa: BLE001 - never kill the coordinator
            _LOGGER.exception("sing-box poll failed: %s", err)
            self._mark_unavailable(err)
            raise UpdateFailed(f"unexpected sing-box error: {err}") from err
        self._last_push_ts = time.monotonic()
        return self.data

    async def _poll_grpc(self) -> None:
        client: SingBoxClient = self.client
        self.data.version, self.data.api_version = await client.get_version()

    async def _poll_clash(self) -> None:
        client: ClashClient = self.client
        groups, proxies = await client.get_proxies()
        self._set_groups(groups, proxies)
        await self._apply_clash_mode()
        await self._apply_clash_connections()

    def _supervise_stream_tasks(self) -> None:
        """Restart stream tasks that died instead of reconnecting."""
        if self._shutdown.is_set() or not self._stream_tasks:
            return
        for index, task in enumerate(self._stream_tasks):
            if not task.done():
                continue
            if task.cancelled():
                _LOGGER.warning("sing-box stream task was cancelled; restarting")
            else:
                exc = task.exception()
                if exc is not None:
                    _LOGGER.error(
                        "sing-box stream task died (%s: %s); restarting",
                        type(exc).__name__,
                        exc,
                    )
                else:
                    _LOGGER.warning("sing-box stream task finished; restarting")
            self._stream_tasks[index] = asyncio.create_task(self._stream_factories[index]())

    # -- streams ------------------------------------------------------------

    async def _pause(self, delay: float) -> bool:
        """Wait before the next reconnect attempt.

        Returns False as soon as a shutdown was requested, so the stream tasks
        end immediately instead of waiting out the whole backoff (up to a
        minute) while Home Assistant is stopping.
        """
        if delay <= 0:
            return True
        try:
            await asyncio.wait_for(self._shutdown.wait(), timeout=max(delay, _MIN_BACKOFF))
        except TimeoutError:
            return True
        return False

    def _stop_if_unsupported(self, name: str, err: Exception) -> bool:
        """Stop a stream the backend simply does not implement.

        A backend without connection tracking answers UNIMPLEMENTED / NOT_FOUND
        to SubscribeConnections. Retrying that forever would only fill the log
        with backoff warnings, so the stream is retired and the websocket API
        reports the feature as unsupported.
        """
        if not isinstance(err, GrpcError) or err.status not in (
            GRPC_STATUS_UNIMPLEMENTED,
            GRPC_STATUS_NOT_FOUND,
        ):
            return False
        _LOGGER.info("sing-box %s stream is not available on this backend: %s", name, err)
        if name == "connections":
            self._connections_supported = False
        self._mark_available()
        return True

    async def _run_stream(self, name: str, stream, apply) -> None:
        """Consume one backend stream, reconnecting with backoff.

        Every exception is caught here: an unhandled error used to kill the
        task silently, leaving ``last_update_success`` True and the entities
        stuck on stale data with nothing in the log.
        """
        backoff = _MIN_BACKOFF
        while True:
            try:
                async for payload in stream():
                    apply(payload)
                    backoff = _MIN_BACKOFF
                    self._mark_available()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the stream alive
                if is_auth_error(err):
                    _LOGGER.error("sing-box %s stream: authentication failed (%s)", name, err)
                    self._mark_unavailable(err)
                    if self.config_entry is not None:
                        self.config_entry.async_start_reauth(self.hass)
                    return
                if self._stop_if_unsupported(name, err):
                    return
                _LOGGER.warning("sing-box %s stream lost: %s", name, err)
            self._mark_unavailable(None)
            if not await self._pause(backoff):
                return
            backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _run_grpc_status_stream(self) -> None:
        await self._run_stream(
            "status",
            lambda: self.client.subscribe_status(self._interval_ns),
            self._apply_status,
        )

    async def _run_groups_stream(self) -> None:
        await self._run_stream("groups", self.client.subscribe_groups, self._apply_groups)

    async def _run_connections_stream(self) -> None:
        if not self._connections_supported:
            return
        await self._run_stream(
            "connections",
            lambda: self.client.subscribe_connections(self._connections_interval_ns),
            self._apply_connection_events,
        )

    async def _run_clash_traffic_stream(self) -> None:
        await self._run_stream("traffic", self.client.traffic_stream, self._apply_traffic)

    async def _run_clash_poll_loop(self) -> None:
        interval = max(self._interval_seconds, POLL_INTERVAL_SECONDS)
        backoff = _MIN_BACKOFF
        while True:
            try:
                groups, proxies = await self.client.get_proxies()
                self._set_groups(groups, proxies)
                await self._apply_clash_mode()
                await self._apply_clash_connections()
                backoff = _MIN_BACKOFF
                self._mark_available()
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001 - keep the loop alive
                if is_auth_error(err):
                    _LOGGER.error("clash API authentication failed: %s", err)
                    self._mark_unavailable(err)
                    if self.config_entry is not None:
                        self.config_entry.async_start_reauth(self.hass)
                    return
                _LOGGER.warning("clash poll failed: %s", err)
                self._mark_unavailable(None)
                if not await self._pause(backoff):
                    return
                backoff = min(backoff * 2, _MAX_BACKOFF)
                continue
            if not await self._pause(interval):
                return

    async def _apply_clash_mode(self) -> None:
        try:
            mode_list, current = await self.client.get_configs()
        except (TimeoutError, ClashApiError, OSError, ConnectionError) as err:
            _LOGGER.warning("clash mode poll failed: %s", err)
            return
        self.data.clash_mode_list = mode_list
        self.data.clash_mode = current
        if not self.clash_mode_available:
            # The clash mode select is created lazily, so let the platforms
            # know that it became available after setup.
            self.clash_mode_available = True
            self._notify_discovery()

    async def _apply_clash_connections(self) -> None:
        try:
            (
                n,
                memory,
                upload_total,
                download_total,
                connections,
            ) = await self.client.get_connections_snapshot()
        except (TimeoutError, ClashApiError, OSError, ConnectionError) as err:
            _LOGGER.warning("clash connections snapshot failed: %s", err)
            return
        self.data.connections_in = n
        self.data.memory = memory
        self.data.uplink_total = upload_total
        self.data.downlink_total = download_total
        # A clash snapshot already is the complete set of live connections,
        # so it replaces whatever was known instead of merging into it.
        self._set_connections(connections)

    # -- snapshot updates ---------------------------------------------------

    def _set_groups(self, groups: list[SingBoxGroup], proxies: list[SingBoxGroupItem]) -> None:
        self.data.groups = groups
        self.data.proxies = proxies
        self._groups_index = {group.tag: group for group in groups}
        self._proxies_index = {proxy.tag: proxy for proxy in proxies}
        self._groups_ready.set()

    def _apply_groups(self, groups: list[SingBoxGroup]) -> None:
        self._set_groups(groups, flatten_proxies(groups))

    def _set_connections(self, connections: list[SingBoxConnection]) -> None:
        """Replace the live connection set with a full snapshot."""
        self._connections = {
            connection.id: connection for connection in connections if connection.id
        }

    def _apply_connection_events(self, update: SingBoxConnectionUpdate) -> None:
        """Weld one SubscribeConnections frame into the live connection map."""
        if update.reset:
            self._connections = {}
        for connection_id in update.closed_ids:
            self._connections.pop(connection_id, None)
        for connection in update.connections:
            if connection.id:
                self._connections[connection.id] = connection
        # ``data.connections_in`` keeps coming from the SubscribeStatus frame
        # (and from the clash snapshot): writing the map size here would make
        # the sensor oscillate between two different numbers every second.

    def _apply_traffic(self, frame: tuple[int, int]) -> None:
        # The WS /traffic frame only carries per-second deltas; the running
        # totals come from /connections, so they are not accumulated here
        # (that would double count what the poll has already reported).
        up, down = frame
        self._add_traffic(up, down)

    def _apply_status(self, fields: dict[int, list[int | bytes]]) -> None:
        self.data.memory = _int(fields, 1)
        self.data.goroutines = _int(fields, 2)
        self.data.connections_in = _int(fields, 3)
        self.data.connections_out = _int(fields, 4)
        self.data.traffic_available = _bool(fields, 5)
        # Fields 6/7 are byte deltas since the previous frame; they are summed
        # and divided by the real elapsed time when the snapshot is pushed.
        self._add_traffic(_int(fields, 6), _int(fields, 7))
        self.data.uplink_total = _int(fields, 8)
        self.data.downlink_total = _int(fields, 9)

    def _add_traffic(self, up: int, down: int) -> None:
        self._rate_up_bytes += max(int(up), 0)
        self._rate_down_bytes += max(int(down), 0)

    def _flush_traffic_rate(self, now: float) -> None:
        elapsed = max(now - self._rate_window_start, _MIN_RATE_WINDOW)
        self.data.uplink = self._rate_up_bytes / elapsed
        self.data.downlink = self._rate_down_bytes / elapsed
        self._rate_up_bytes = 0
        self._rate_down_bytes = 0
        self._rate_window_start = now

    def _push_due(self) -> bool:
        return time.monotonic() - self._last_push_ts >= self._push_interval

    def _mark_available(self) -> None:
        """Note that the backend is alive; push at most every _push_interval."""
        now = time.monotonic()
        recovering = not self.last_update_success
        if recovering:
            # Recover immediately so entities flip back to available.
            self.last_update_success = True
            self._flush_traffic_rate(now)
            self._last_push_ts = now
            self.async_set_updated_data(self.data)
            self._notify_discovery()
            return
        if now - self._last_push_ts < self._push_interval:
            return
        self._flush_traffic_rate(now)
        self._last_push_ts = now
        self.async_set_updated_data(self.data)
        self._notify_discovery()

    def _mark_unavailable(self, err: Exception | None) -> None:
        if self.last_update_success:
            _LOGGER.warning("sing-box became unavailable%s", f": {err}" if err else "")
        self.last_update_success = False
        self.async_update_listeners()

    # -- lookups ------------------------------------------------------------

    @property
    def stream_tasks(self) -> list[asyncio.Task]:
        """The running backend stream tasks (for diagnostics)."""
        return list(self._stream_tasks)

    @property
    def connections_supported(self) -> bool:
        """False when the backend cannot report the connection list at all."""
        return self._connections_supported

    @property
    def connections(self) -> list[SingBoxConnection]:
        """The live connections, in the order the backend reported them."""
        return list(self._connections.values())

    @property
    def groups_index(self) -> dict[str, SingBoxGroup]:
        return self._groups_index

    @property
    def proxies_index(self) -> dict[str, SingBoxGroupItem]:
        return self._proxies_index

    def group(self, tag: str) -> SingBoxGroup | None:
        return self._groups_index.get(tag)

    def proxy(self, tag: str) -> SingBoxGroupItem | None:
        return self._proxies_index.get(tag)

    # -- control helpers (called by services/entities) ----------------------

    async def select_outbound(self, group_tag: str, outbound_tag: str) -> None:
        await self.client.select_outbound(group_tag, outbound_tag)

    async def set_group_expand(self, group_tag: str, is_expand: bool) -> None:
        if self.backend != BACKEND_GRPC:
            raise SingBoxNotSupported("expanding a group is not supported by the clash API backend")
        await self.client.set_group_expand(group_tag, is_expand)

    async def url_test(self, outbound_tag: str, url: str | None = None) -> None:
        if self.backend == BACKEND_GRPC:
            await self.client.url_test(outbound_tag)
            return
        await self.client.url_test(outbound_tag, url)

    async def close_connection(self, connection_id: str) -> None:
        await self.client.close_connection(connection_id)

    async def close_all_connections(self) -> None:
        await self.client.close_all_connections()

    async def set_clash_mode(self, mode: str) -> None:
        await self.client.set_clash_mode(mode)
        self.data.clash_mode = mode
        self.async_set_updated_data(self.data)
