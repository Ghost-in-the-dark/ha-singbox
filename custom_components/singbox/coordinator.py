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
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .backend import BACKEND_GRPC
from .clash import (
    POLL_INTERVAL_SECONDS,
    ClashApiError,
    ClashClient,
    PingResult,
    _now_ms,
    is_auth_error,
)
from .const import DEFAULT_HISTORY, DEFAULT_UPDATE_INTERVAL, DOMAIN
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


# ---------------------------------------------------------------------------
# Per-outbound traffic attribution
# ---------------------------------------------------------------------------

# How many sample windows a tag survives after its last connection closed.
# Dropping it immediately makes an "active now" filter flicker: a tag
# disappears for a window whenever its last connection is closed by the
# server, and a short grace period hides that without inventing traffic.
_TRAFFIC_TAG_GRACE = 2

# A window shorter than this is not a measurement: two snapshots delivered
# back to back would be divided by a few milliseconds and report a nonsense
# speed. The clash poll never runs faster than POLL_INTERVAL_SECONDS, so this
# only guards against a reconnect delivering an extra snapshot.
_MIN_TRAFFIC_WINDOW = 0.5

# Consecutive failed polls of a healthy router are normal; without this
# hysteresis every traffic sensor would flip to unavailable and back when a
# single request times out.
_TRAFFIC_STALE_AFTER = 30.0


@dataclass(frozen=True)
class TrafficSample:
    """One distilled per-outbound traffic reading."""

    #: tag -> (up, down) bytes per second of the window that just ended.
    rates: dict[str, tuple[int, int]]
    #: Summed speed over all connections. NOT the sum of ``rates``: one
    #: connection is attributed to every tag of its outbound chain.
    total: tuple[int, int]
    #: ISO-8601 moment the window was closed.
    sampled_at: str
    #: Measured length of the window, in seconds.
    window_seconds: float


class OutboundTrafficSampler:
    """Turn two connection snapshots into bytes/second per outbound tag.

    sing-box has no per-outbound counter endpoint. What it does expose is the
    full connection list, where every connection carries the outbound chain
    that handled it plus its own cumulative byte counters. Two consecutive
    snapshots of that list therefore reveal the traffic of every outbound: the
    increment of the counters of a connection, attributed to each tag of its
    chain, divided by the real elapsed time.

    The rules that keep the numbers honest:

    * Only connections present in both snapshots contribute. A connection seen
      for the first time already carries the bytes of its initial burst, so
      counting them would fabricate a spike on every new download.
    * A negative increment counts as zero: the counters are cumulative per
      connection and only go down when sing-box reused the id for a new one.
    * The increment is added to every tag of the chain (group, node, leaf), so
      the card can show the speed of a node and of the group it belongs to.
      The per-tag numbers therefore overlap and their sum exceeds the traffic
      of a single connection; ``total`` keeps the real figure.
    * The rate is divided by the measured elapsed time, not by the nominal
      poll interval, because the poll drifts.
    * An outbound that still has a connection but moved no bytes is reported
      with a zero rate, so the card keeps listing it between transfers.
    * A tag whose connections are all gone keeps a zero rate for a couple of
      windows before it is dropped, so the entity registry does not churn.
    """

    def __init__(self) -> None:
        # id -> (upload, download) of the previous snapshot.
        self._previous: dict[str, tuple[int, int]] = {}
        # tag -> [up_bytes, down_bytes] accumulated since the last sample.
        self._window: dict[str, list[int]] = {}
        # tag -> windows left before it is dropped from the published rates.
        self._missed: dict[str, int] = {}
        self._window_start: float | None = None
        self._previous_totals: tuple[int, int] | None = None
        self._window_up = 0
        self._window_down = 0
        self._rates: dict[str, tuple[int, int]] = {}
        self._total: tuple[int, int] = (0, 0)
        self._sampled_at = ""
        self._window_seconds = 0.0
        self.windows = 0

    # -- sampling -----------------------------------------------------------

    def sample(
        self,
        connections: list[SingBoxConnection],
        totals: tuple[int, int],
        now: float,
    ) -> TrafficSample | None:
        """Fold one connection snapshot in and return the new sample.

        Returns None for the very first snapshot (a rate needs two points in
        time) and for one that arrives too soon after its predecessor.
        """
        if self._window_start is None:
            self._remember(connections, totals, now)
            return None
        elapsed = now - self._window_start
        if elapsed < _MIN_TRAFFIC_WINDOW:
            # Keep the baseline instead of throwing the accumulated bytes away.
            return None
        self._accumulate(connections, totals)
        rates = self._flush(elapsed, connections)
        self._rates = rates
        self._sampled_at = datetime.now().astimezone().isoformat(timespec="seconds")
        self._window_seconds = elapsed
        self.windows += 1
        self._remember(connections, totals, now)
        return TrafficSample(
            rates=dict(rates),
            total=self._total,
            sampled_at=self._sampled_at,
            window_seconds=elapsed,
        )

    def _remember(
        self,
        connections: list[SingBoxConnection],
        totals: tuple[int, int],
        now: float,
    ) -> None:
        """Store the current snapshot as the baseline for the next one."""
        self._previous = {
            connection.id: (connection.upload_total, connection.download_total)
            for connection in connections
            if connection.id
        }
        self._previous_totals = totals
        self._window_start = now

    def _accumulate(
        self,
        connections: list[SingBoxConnection],
        totals: tuple[int, int],
    ) -> None:
        """Add the per-connection increments of this window to the tag buckets."""
        counted_up = 0
        counted_down = 0
        for connection in connections:
            previous = self._previous.get(connection.id) if connection.id else None
            if previous is None:
                # First appearance: nothing here can be pinned to this window.
                continue
            up_delta = connection.upload_total - previous[0]
            down_delta = connection.download_total - previous[1]
            # A reset (or a reused id) is not negative traffic.
            up_delta = up_delta if up_delta > 0 else 0
            down_delta = down_delta if down_delta > 0 else 0
            counted_up += up_delta
            counted_down += down_delta
            if not up_delta and not down_delta:
                continue
            # dict.fromkeys keeps the order and drops a duplicate tag: a chain
            # naming the same outbound twice is still one attribution.
            for tag in dict.fromkeys(connection.chain):
                bucket = self._window.setdefault(tag, [0, 0])
                bucket[0] += up_delta
                bucket[1] += down_delta
        self._window_up = counted_up
        self._window_down = counted_down
        self._log_discrepancy(counted_up, counted_down, totals)

    def _log_discrepancy(
        self,
        counted_up: int,
        counted_down: int,
        totals: tuple[int, int],
    ) -> None:
        """Compare the attributed bytes with the global counter delta.

        On an idle router the two nearly match; the difference is the traffic
        of connections that closed inside the window (their bytes were counted
        and then vanished from the snapshot). DEBUG, because it is a debugging
        aid, not a warning.
        """
        if self._previous_totals is None:
            return
        global_up = totals[0] - self._previous_totals[0]
        global_down = totals[1] - self._previous_totals[1]
        if global_up < 0 or global_down < 0:
            # sing-box restarted between the snapshots; the comparison is void.
            return
        _LOGGER.debug(
            "outbound traffic window %d: counted %d up / %d down, global delta "
            "%d up / %d down, unattributed %d up / %d down (closed connections)",
            self.windows + 1,
            counted_up,
            counted_down,
            global_up,
            global_down,
            global_up - counted_up,
            global_down - counted_down,
        )

    def _flush(
        self,
        elapsed: float,
        connections: list[SingBoxConnection],
    ) -> dict[str, tuple[int, int]]:
        """Convert the window buckets to rates and roll the tag bookkeeping."""
        rates: dict[str, tuple[int, int]] = {
            tag: (round(up / elapsed), round(down / elapsed))
            for tag, (up, down) in self._window.items()
        }
        self._total = (round(self._window_up / elapsed), round(self._window_down / elapsed))
        self._window = {}
        # A tag with an idle but still open connection is not gone, it just
        # moved no bytes - that is what a zero rate means, and reporting it
        # keeps the card from hiding an outbound that is between transfers.
        # Only a tag with no connection at all gets the grace countdown.
        present = {tag for connection in connections for tag in connection.chain}
        for tag in set(self._rates) | present:
            if tag in rates or tag in present:
                self._missed.pop(tag, None)
                rates.setdefault(tag, (0, 0))
                continue
            missed = self._missed.get(tag, 0) + 1
            if missed <= _TRAFFIC_TAG_GRACE:
                self._missed[tag] = missed
                rates[tag] = (0, 0)
            else:
                self._missed.pop(tag, None)
        return rates

    # -- published state ----------------------------------------------------

    @property
    def rates(self) -> dict[str, tuple[int, int]]:
        """The latest bytes/second per outbound tag."""
        return dict(self._rates)

    @property
    def total(self) -> tuple[int, int]:
        """The latest summed speed over all connections."""
        return self._total

    @property
    def sampled_at(self) -> str:
        """ISO-8601 timestamp of the last closed window ("" before one)."""
        return self._sampled_at

    def reset(self) -> None:
        """Forget the baseline after the backend went away or restarted."""
        self._previous = {}
        self._window = {}
        self._missed = {}
        self._window_start = None
        self._previous_totals = None
        self._window_up = 0
        self._window_down = 0
        self._rates = {}
        self._total = (0, 0)
        self._sampled_at = ""
        self._window_seconds = 0.0
        self.windows = 0


class SingBoxCoordinator(DataUpdateCoordinator[SingBoxStatus]):
    """Manages the sing-box API connection and its push streams."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SingBoxClient | ClashClient,
        backend: str,
        update_interval_seconds: int = DEFAULT_UPDATE_INTERVAL,
        history_enabled: bool = DEFAULT_HISTORY,
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
        # Whether the entities of this entry write to the recorder. Read by
        # the sensor platform (to skip new ping entities entirely) and by the
        # websocket status command (to tell the card where pings come from).
        self.history_enabled = bool(history_enabled)
        # Last url-test outcome per outbound tag, backend-neutral. The clash
        # client fills it itself; on the gRPC backend the coordinator records
        # the result of url_test() so both expose the same thing.
        self.last_pings: dict[str, PingResult] = {}
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
        # Per-outbound traffic. The clash backend derives it from two
        # consecutive connection snapshots; the gRPC backend has no
        # cumulative per-connection counters to diff (its frames are deltas
        # with an explicit reset flag), so the sampler is left out and the
        # feature reports itself unavailable there instead of guessing.
        self._traffic_sampler = None if backend == BACKEND_GRPC else OutboundTrafficSampler()
        self._traffic_listeners: list = []
        # Tags of the live connections of the last snapshot, i.e. outbounds
        # that currently carry traffic. Kept apart from the sampler's rates,
        # which hold a vanished tag for a couple of windows.
        self._traffic_tags: set[str] = set()
        # time.monotonic() of the last completed sample, for the staleness
        # check of outbound_traffic_available.
        self._traffic_sample_monotonic = 0.0
        # The payload the websocket API and the card read; kept on the
        # snapshot so diagnostics can show it too.
        self.data.traffic = {
            "available": False,
            "now": "",
            "outbounds": {},
            "total": {"up": 0, "down": 0},
        }

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
        # Optional endpoints are probed once: the premium/PDK builds add
        # /group batch tests and real /rules, upstream 1.14.4 has the former
        # but not the latter. A build without them keeps working, it just
        # loses the feature (see clash.detect_capabilities).
        try:
            await client.detect_capabilities()
        except (TimeoutError, OSError, ConnectionError, ClashApiError) as err:
            _LOGGER.debug("clash API capability probe failed: %s", err)
        self.data.premium = client.premium
        self.data.meta = client.meta
        self.data.rules_available = client.rules_available
        self.data.group_delay_available = client.group_delay_available
        # The capabilities probe already established whether /rules answers a
        # real list (premium) or null (upstream). Reading it once here means a
        # diagnostics download shows the route set without the user having to
        # call the refresh_rules service first; failures stay non-fatal.
        if client.rules_available:
            try:
                self.data.rules = await client.get_rules()
            except (TimeoutError, OSError, ConnectionError, ClashApiError) as err:
                _LOGGER.debug("route rules unavailable: %s", err)

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
        self._sample_outbound_traffic(connections, (upload_total, download_total))

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
    def rules_available(self) -> bool:
        """True when the backend can list the route rules (premium builds)."""
        return bool(self.data.rules_available)

    @property
    def premium(self) -> bool:
        """True when /version advertises the premium/PDK clash-API extras."""
        return bool(self.data.premium)

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

    # -- per-outbound traffic -----------------------------------------------

    @callback
    def async_add_traffic_listener(self, update_callback) -> None:
        """Register a callback invoked whenever a new traffic sample lands."""
        self._traffic_listeners.append(update_callback)

    @callback
    def async_remove_traffic_listener(self, update_callback) -> None:
        """Remove a traffic callback."""
        self._traffic_listeners.remove(update_callback)

    @callback
    def _notify_traffic(self) -> None:
        for update_callback in list(self._traffic_listeners):
            update_callback()

    def _sample_outbound_traffic(
        self,
        connections: list[SingBoxConnection],
        totals: tuple[int, int],
    ) -> None:
        """Fold one connection snapshot into the per-outbound traffic sample.

        Called right after a clash connections poll: that poll is the only
        place where the full list (and therefore the per-connection counters)
        is fetched anyway, so the traffic numbers cost no extra request.
        """
        if self._traffic_sampler is None:
            return
        known = self._traffic_tags
        sample = self._traffic_sampler.sample(connections, totals, time.monotonic())
        # The live tags come from the snapshot, not from the sample: the
        # sample deliberately keeps a vanished tag around for a couple of
        # windows, while "does this outbound still exist" must answer now.
        self._traffic_tags = {tag for connection in connections for tag in connection.chain}
        if sample is None:
            return
        self._traffic_sample_monotonic = time.monotonic()
        self.data.traffic = self.traffic_payload()
        new_tags = self._traffic_tags - known
        if new_tags:
            _LOGGER.debug("new outbounds with traffic: %s", ", ".join(sorted(new_tags)))
        # Listeners first (the sensor platform creates one entity pair per new
        # tag), then the general discovery pass so the group/proxy listeners
        # see a subscription change in the same push.
        self._notify_traffic()
        if new_tags:
            self._notify_discovery()

    def traffic_payload(self) -> dict:
        """The per-outbound traffic block of the ``singbox/status`` command.

        ``available`` is False when the backend cannot report per-connection
        counters (the gRPC backend, or a build without connection tracking):
        the card then hides the traffic column instead of showing zeros as if
        the router were idle. ``now`` is the moment the last window closed.
        ``total`` is the summed speed over all connections, kept apart from
        the per-tag numbers because one connection is attributed to every
        outbound of its chain, so those deliberately overlap.
        """
        return {
            "available": self.outbound_traffic_available,
            "now": self.outbound_traffic_sampled_at,
            "outbounds": {
                tag: {"up": up, "down": down} for tag, (up, down) in self.outbound_traffic.items()
            },
            "total": {
                "up": self.outbound_traffic_total[0],
                "down": self.outbound_traffic_total[1],
            },
        }

    @property
    def outbound_traffic(self) -> dict[str, tuple[int, int]]:
        """Bytes/second per outbound tag, keyed by tag (a copy).

        Tags the sampler is still holding through its grace period are
        included with a zero rate; :meth:`outbound_tags` answers which of
        them still exist upstream.
        """
        if self._traffic_sampler is None:
            return {}
        return self._traffic_sampler.rates

    @property
    def outbound_traffic_total(self) -> tuple[int, int]:
        """Summed bytes/second over every connection of the last window."""
        if self._traffic_sampler is None:
            return (0, 0)
        return self._traffic_sampler.total

    @property
    def outbound_traffic_available(self) -> bool:
        """True when there is a recent per-outbound sample to show.

        A sample older than _TRAFFIC_STALE_AFTER is not used: the poll loop
        may be down while the integration is still "available" on its other
        data, and stale rates would silently look live.
        """
        if self._traffic_sampler is None or not self._connections_supported:
            return False
        if not self._traffic_sample_monotonic:
            return False
        return time.monotonic() - self._traffic_sample_monotonic <= _TRAFFIC_STALE_AFTER

    @property
    def outbound_traffic_sampled_at(self) -> str:
        """ISO-8601 moment the last traffic window was closed ("" before one)."""
        if self._traffic_sampler is None:
            return ""
        return self._traffic_sampler.sampled_at

    def outbound_tags(self) -> list[str]:
        """Outbound tags that carry traffic right now, in a stable order.

        This is the list the sensor platform creates entities for, so it is
        sorted: an outbound must keep the same position across restarts to
        keep the entity registry stable.
        """
        return sorted(self._traffic_tags)

    def has_outbound_traffic(self, tag: str) -> bool:
        """True while this tag is part of a live connection chain."""
        return tag in self._traffic_tags

    # -- control helpers (called by services/entities) ----------------------

    async def select_outbound(self, group_tag: str, outbound_tag: str) -> None:
        await self.client.select_outbound(group_tag, outbound_tag)

    async def set_group_expand(self, group_tag: str, is_expand: bool) -> None:
        if self.backend != BACKEND_GRPC:
            raise SingBoxNotSupported("expanding a group is not supported by the clash API backend")
        await self.client.set_group_expand(group_tag, is_expand)

    async def url_test(self, outbound_tag: str, url: str | None = None) -> PingResult:
        """Run a url-test and return its outcome; never raise on a failed test.

        A node that cannot reach the test URL is a normal state of a proxy
        list, not an integration failure: the service returns the outcome and
        the card paints that node red, instead of Home Assistant showing the
        full-screen "Failed to perform the action singbox/url_test" banner.
        Only authentication and transport errors still propagate.
        """
        if self.backend == BACKEND_GRPC:
            await self.client.url_test(outbound_tag)
            result = PingResult(tag=outbound_tag, test_time=_now_ms())
        else:
            result = await self.client.url_test(outbound_tag, url)
        self.last_pings[result.tag] = result
        return result

    async def url_test_many(self, tags: list[str], url: str | None = None) -> dict[str, PingResult]:
        """Test several outbounds, batching through the clash group endpoint."""
        if self.backend == BACKEND_GRPC:
            results: dict[str, PingResult] = {}
            for tag in tags:
                results[tag] = await self.url_test(tag, url)
            return results
        results = await self.client.url_test_many(tags, url)
        self.last_pings.update(results)
        return results

    def ping_for(self, tag: str) -> PingResult | None:
        """Latest known url-test outcome for an outbound tag."""
        if self.backend == BACKEND_GRPC:
            return self.last_pings.get(tag)
        return self.client.last_pings.get(tag) or self.last_pings.get(tag)

    async def reload_config(self, force: bool = True) -> None:
        """Re-apply the running config (premium builds answer this)."""
        if self.backend == BACKEND_GRPC:
            raise SingBoxNotSupported("reloading the config is not supported by the gRPC backend")
        await self.client.reload_config(force)

    async def flush_fakeip_cache(self) -> None:
        if self.backend == BACKEND_GRPC:
            raise SingBoxNotSupported("flushing the fake-IP cache needs the clash API backend")
        await self.client.flush_fakeip_cache()

    async def flush_dns_cache(self) -> None:
        if self.backend == BACKEND_GRPC:
            raise SingBoxNotSupported("flushing the DNS cache needs the clash API backend")
        await self.client.flush_dns_cache()

    async def refresh_rules(self) -> None:
        """Re-read the route rules and expose them on the snapshot."""
        if self.backend == BACKEND_GRPC:
            raise SingBoxNotSupported("listing route rules needs the clash API backend")
        self.data.rules = await self.client.get_rules()
        self.data.rules_available = bool(self.data.rules)
        self.async_set_updated_data(self.data)

    async def dns_query(self, name: str, record_type: str = "A") -> dict:
        if self.backend == BACKEND_GRPC:
            raise SingBoxNotSupported("DNS queries need the clash API backend")
        return await self.client.dns_query(name, record_type)

    async def close_connection(self, connection_id: str) -> None:
        await self.client.close_connection(connection_id)

    async def close_all_connections(self) -> None:
        await self.client.close_all_connections()

    async def set_clash_mode(self, mode: str) -> None:
        await self.client.set_clash_mode(mode)
        self.data.clash_mode = mode
        self.async_set_updated_data(self.data)
