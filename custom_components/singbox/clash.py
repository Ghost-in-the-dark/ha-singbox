"""Minimal client for the sing-box ``clash_api`` (Clash REST + WebSocket).

sing-box exposes a Clash-compatible REST API at its ``experimental.clash_api``
external controller. Unlike the gRPC ``api`` service (sing-box >= 1.14.0) it
works on every sing-box 1.11+ build, which makes it the fallback backend for
platforms where 1.14.0 is not yet packaged (e.g. OpenWrt).

Verified against sing-box 1.14.0 (clash_api):

* ``GET /version`` -> ``{"meta": true, "premium": true, "version": "sing-box 1.14.0"}``
* ``GET /configs``  -> mode / mode-list
* ``PUT /configs``  with ``{"mode": ...}`` -> 204
* ``GET /proxies``  -> ``{"proxies": {name: {type, now, all, ...}}}``
* ``PUT /proxies/{name}/`` with ``{"name": target}`` -> 204 (trailing slash
  is required, the classic ``/proxies/{group}/{name}`` path is not routed)
* ``GET /proxies/{name}/delay?url=...&timeout=...`` -> ``{"delay": ms}``
* ``GET /connections/`` -> JSON snapshot (no WebSocket upgrade header)
* ``WS /traffic``     -> ``{"up": n, "down": n}`` deltas every second
* ``WS /connections`` -> snapshots on change
* ``DELETE /connections/`` (all) and ``DELETE /connections/{id}``
* Auth: ``Authorization: Bearer <secret>`` -> 401 without it

Compatibility with the "premium" / PDK builds
==============================================

Sing-box ships in several flavours: the upstream release, and builds that
report ``premium: true`` / ``meta: true`` from ``/version`` (the PDK fork,
"sing-box 1.14.4-pdk-...", and the mihomo-flavoured distributions). They
expose the same clash controller, with a few extra or missing pieces.
Measured against upstream 1.14.4 and sing-box 1.14.4-pdk:

============================  ==========  ============
endpoint                      upstream    premium
============================  ==========  ============
``GET /version``              yes         yes (+meta)
``GET /configs``, ``/proxies`` yes        yes
``GET /group``                yes         yes
``GET /group/{tag}/delay``    yes         yes
``GET /rules``                null list   real rules
``GET /providers/proxies``    stub {}     stub {}
``GET /dns/query``            yes         yes
``POST /cache/fakeip/flush``  yes         yes
``POST /upgrade/ui``          404         200
============================  ==========  ============

So the premium additions are *optional extras*, never requirements: every
call this module makes has to keep working when the extra endpoint answers
404 or an empty payload, and the client must never treat "this build does
not have feature X" as a fatal error. That is what the capability flags on
:class:`ClashClient` are for.

A second, more subtle difference: a proxy *tag* is arbitrary user text
("My servers: EU2", "ru: Game_ru", emoji, spaces). Embedded slashes would
break the path, so tags are percent-encoded with ``quote(safe="")``.
Upstream and premium both accept that form.

Only aiohttp is used, which ships with Home Assistant.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import aiohttp

from .errors import SingBoxAuthError, SingBoxError, SingBoxNotSupported
from .grpc import (
    GRPC_STATUS_UNAUTHENTICATED,
    SingBoxConnection,
    SingBoxGroup,
    SingBoxGroupItem,
)

_LOGGER = logging.getLogger(__package__)

# URL used when the url_test service is invoked without an explicit target.
DEFAULT_URL_TEST_URL = "https://www.gstatic.com/generate_204"
_URL_TEST_TIMEOUT_MS = 5000
# If no WebSocket frame arrives for this long the stream is considered dead.
_WS_IDLE_TIMEOUT = 45.0
# aiohttp gained the receive(timeout=...) argument in 3.10; older releases
# (still shipped by some Home Assistant builds) need an explicit wait_for.
_WS_RECEIVE_TIMEOUT_ARG = (
    "timeout" in inspect.signature(aiohttp.ClientWebSocketResponse.receive).parameters
)
# The polling loop refreshes groups/config/connection totals on this cadence.
POLL_INTERVAL_SECONDS = 5

# Group types the clash API lets the user switch with PUT /proxies/{group}/.
# sing-box accepts that call only for *group.Selector: urltest and fallback
# groups answer HTTP 400 "Must be a Selector". Creating select entities for
# them made every switch from Home Assistant / the panel card fail.
_SELECTABLE_GROUP_TYPES = frozenset({"Selector"})

# Group types the clash API can batch-test with GET /group/{tag}/delay.
# Upstream answers 404 for a leaf outbound and for GLOBAL, and the premium
# builds answer 404 for anything that is not a group, so the caller falls back
# to the per-proxy endpoint for those. Reject groups cannot be tested at all.
_GROUP_DELAY_TYPES = frozenset({"Selector", "URLTest", "Fallback", "LoadBalance"})

# Outbounds that can never answer a url-test. GLOBAL is the synthetic clash-API
# group (it is a Fallback over *all* outbounds, has no backing sing-box outbound
# and answers 404), and Reject/Block fail every test by construction: probing
# them is what used to raise "An error occurred in the delay test" (HTTP 503)
# for the "block" outbound and paint a red "action failed" banner in the UI.
_UNTESTABLE_TYPES = frozenset({"Reject", "RejectDrop", "Block", "Pass", "Dns"})
_UNTESTABLE_TAGS = frozenset({"GLOBAL", "REJECT", "REJECT-DROP", "PASS", "COMPATIBLE"})
_UNTESTABLE_TAGS_UPPER = frozenset(tag.upper() for tag in _UNTESTABLE_TAGS)


# Guards the "now" walk in _last_url_test_delay. A selector may point at a
# group that points back at it; without a bound the walk recursed until
# Python raised RecursionError, which made every /proxies poll fail.
_MAX_NOW_DEPTH = 32


def _last_url_test_delay(info: dict, all_proxies: dict) -> tuple[int, int]:
    """Return (delay_ms, time_ms) of the newest history entry of a proxy.

    Falls back to the currently selected proxy for groups whose own history
    is empty (Selector groups never record one; UrlTest groups do). The walk
    is iterative and keeps a "seen" set, so cyclic or dangling "now" chains
    return (0, 0) instead of recursing forever.
    """
    seen: set[str] = set()
    current = info
    for _ in range(_MAX_NOW_DEPTH):
        history = current.get("history")
        if isinstance(history, list):
            for entry in reversed(history):
                if not isinstance(entry, dict):
                    continue
                delay = entry.get("delay")
                if isinstance(delay, int) and delay > 0:
                    tested_at = entry.get("time")
                    return delay, tested_at if isinstance(tested_at, int) else 0
        now = current.get("now")
        if not isinstance(now, str) or now in seen:
            return 0, 0
        seen.add(now)
        target = all_proxies.get(now)
        if not isinstance(target, dict) or target is current:
            return 0, 0
        current = target
    return 0, 0


@dataclass
class PingResult:
    """Outcome of one url-test, in the shape the card and the sensors need.

    ``delay`` is 0 when the test failed or has not run; ``failed`` says which
    of the two it was. Keeping them apart matters: a failed test is a real
    answer ("this outbound cannot reach the URL") and is drawn in red, while
    "no data yet" is drawn as a neutral dash.

    ``test_time`` is epoch milliseconds, matching the gRPC backend's
    ``url_test_time`` so both backends feed the same sensor attribute.
    """

    tag: str
    delay: int = 0
    failed: bool = False
    test_time: int = 0


def is_testable_proxy(tag: str, info: dict | None) -> bool:
    """True when a url-test of this outbound can succeed at all.

    Two kinds of outbound can never answer: the synthetic ``GLOBAL`` group
    (no backing sing-box outbound, always 404) and the reject/block outbounds
    (they fail by construction, HTTP 503). Testing them produced an error
    banner for every batch ping, so they are filtered out before the call.
    """
    if tag.upper() in _UNTESTABLE_TAGS_UPPER:
        return False
    if isinstance(info, dict) and str(info.get("type", "")) in _UNTESTABLE_TYPES:
        return False
    return True


def parse_group_delay(payload: object) -> dict[str, int]:
    """Unpack a ``GET /group/{tag}/delay`` reply into {member tag: ms}.

    Upstream and premium both answer with a flat object keyed by the group's
    members, e.g. ``{"eu: EU2": 152, "eu: EU-openwrt": 130}``.
    Entries whose delay is not a usable number are dropped instead of being
    reported as 0, because 0 means "failed" everywhere else.
    """
    if not isinstance(payload, dict):
        return {}
    result: dict[str, int] = {}
    for tag, delay in payload.items():
        if not isinstance(tag, str):
            continue
        if isinstance(delay, bool) or not isinstance(delay, int):
            continue
        result[tag] = delay if delay > 0 else 0
    return result


def _best_delay(delays) -> int:
    """Smallest usable (positive) delay of a group's members, 0 if none.

    sing-box reports a failed member as 0 in a group delay reply, so the zeros
    say "this node failed", not "this node is instant". The smallest positive
    value is the delay the group would actually route to, i.e. what the
    group's ping means to a user. min() over the positives is deliberate:
    max() reported the slowest node instead (a 176 ms group showed as 820 ms).
    """
    positive = [delay for delay in delays if isinstance(delay, int) and delay > 0]
    return min(positive) if positive else 0


def _endpoint(addr: object, port: object) -> str:
    """Render a clash metadata address/port pair as "ip:port"."""
    host = addr if isinstance(addr, str) else ""
    if port is None or port == "":
        return host
    return f"{host}:{port}"


def _now_ms() -> int:
    """Current wall-clock time in epoch milliseconds."""
    return int(datetime.now().timestamp() * 1000)


def _parse_epoch_ms(value: object) -> int:
    """Convert a clash ``start`` timestamp to epoch milliseconds.

    sing-box marshals the Go ``time.Time`` as RFC 3339 with nanoseconds
    ("2026-11-01T19:20:13.123456789+03:00"); classic clash builds send the
    same string, while a few forks send a numeric Unix time instead.
    """
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        # Heuristic: seconds vs milliseconds.
        number = float(value)
        return int(number * 1000) if number < 1e11 else int(number)
    if not isinstance(value, str) or not value:
        return 0
    try:
        return int(datetime.fromisoformat(value).timestamp() * 1000)
    except ValueError:
        pass
    try:
        return int(float(value) * 1000)
    except ValueError:
        return 0


def _parse_clash_connection(raw: dict) -> SingBoxConnection:
    """Flatten one ``/connections`` entry into the shared connection model.

    The snapshot replaces the flat ``SingBoxConnection`` fields with a nested
    ``metadata`` object and keeps the byte counters as totals; the card works
    with the same flat shape for both backends, so everything is unpacked
    here.
    """
    metadata = raw.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    chain = [item for item in raw.get("chains") or [] if isinstance(item, str)]
    process = metadata.get("processPath") or metadata.get("process") or ""
    upload_total = raw.get("upload")
    download_total = raw.get("download")
    return SingBoxConnection(
        id=str(raw.get("id", "")),
        network=str(metadata.get("network", "") or ""),
        # The clash snapshot has no sniffed protocol field; ``type`` is the
        # inbound type ("tun", "http/tun"), not a protocol.
        protocol="",
        source=_endpoint(metadata.get("sourceIP"), metadata.get("sourcePort")),
        destination=_endpoint(metadata.get("destinationIP"), metadata.get("destinationPort")),
        host=str(metadata.get("host") or metadata.get("domain") or ""),
        rule=str(raw.get("rule", "") or ""),
        # sing-box reports the chain outermost-group-first and the final
        # outbound last, which is exactly what the card renders.
        outbound=chain[-1] if chain else "",
        chain=chain,
        process=process if isinstance(process, str) else "",
        upload_total=upload_total if isinstance(upload_total, int) else 0,
        download_total=download_total if isinstance(download_total, int) else 0,
        created_at=_parse_epoch_ms(raw.get("start")),
    )


def parse_connections_snapshot(
    data: object,
) -> tuple[list[SingBoxConnection], int, int, int]:
    """Unpack a ``GET /connections/`` payload.

    Returns (connections, memory, upload_total, download_total). A payload
    without a usable ``connections`` array yields an empty list instead of
    raising: older clash builds and sing-box forks answer slightly different
    shapes, and a missing list must not take the poll loop down.
    """
    if not isinstance(data, dict):
        raise ClashApiError(200, f"unexpected /connections response: {type(data).__name__}")
    raw_connections = data.get("connections")
    connections: list[SingBoxConnection] = []
    if isinstance(raw_connections, list):
        for raw in raw_connections:
            if isinstance(raw, dict):
                connections.append(_parse_clash_connection(raw))
    return (
        connections,
        data.get("memory", 0) if isinstance(data.get("memory", 0), int) else 0,
        data.get("uploadTotal", 0) if isinstance(data.get("uploadTotal", 0), int) else 0,
        data.get("downloadTotal", 0) if isinstance(data.get("downloadTotal", 0), int) else 0,
    )


class ClashApiError(SingBoxError):
    """A clash API call failed with a non-success status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"clash API HTTP {status}: {message}")
        self.status = status


class ClashApiAuthError(ClashApiError, SingBoxAuthError):
    """The clash API rejected the configured secret (HTTP 401)."""


def is_auth_error(err: BaseException) -> bool:
    """True when the error means "the configured secret is wrong"."""
    return isinstance(err, SingBoxAuthError) or getattr(err, "status", 0) in (
        401,
        GRPC_STATUS_UNAUTHENTICATED,
    )


class ClashClient:
    """Async client for the sing-box clash_api external controller."""

    def __init__(
        self,
        host: str,
        port: int,
        secret: str = "",
        use_tls: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        scheme = "https" if use_tls else "http"
        self._base_url = f"{scheme}://{host}:{int(port)}"
        self._secret = secret
        self._session = session
        self._own_session = session is None
        self._ws: list[aiohttp.ClientWebSocketResponse] = []
        # Feature flags, filled by detect_capabilities(). They default to the
        # conservative upstream answer (no premium extras) so a client that
        # never ran detection behaves like sing-box <= 1.14.0: everything
        # optional is skipped instead of being requested and failing.
        self.premium = False
        self.meta = False
        self.group_delay_available = False
        self.rules_available = False
        # Last url-test outcome per outbound tag. Populated by url_test() and
        # url_test_many(); the sensors and the websocket status command read
        # it so a failed test is distinguishable from "never tested".
        self.last_pings: dict[str, PingResult] = {}

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._secret}"} if self._secret else {}

    async def _request_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        for ws in self._ws:
            try:
                # sing-box's ws server never answers the close handshake, so
                # bound the wait or shutdown would stall for seconds.
                await asyncio.wait_for(ws.close(), timeout=2)
            except (TimeoutError, ConnectionError, OSError):
                pass
        self._ws.clear()
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> tuple[int, bytes]:
        session = await self._request_session()
        try:
            async with session.request(
                method,
                self._url(path),
                json=json_body,
                params=params,
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                body = await resp.read()
        except aiohttp.ClientError as err:
            raise ConnectionError(
                f"cannot reach sing-box clash API at {self._base_url}: {err}"
            ) from err
        return resp.status, body

    async def _json(self, method: str, path: str, **kwargs: Any) -> Any:
        status, body = await self._request(method, path, **kwargs)
        if status >= 400:
            message = body.decode(errors="replace").strip()[:200]
            raise ClashApiError(status, message)
        if not body:
            return None
        try:
            return json.loads(body)
        except ValueError as err:
            raise ClashApiError(status, f"invalid JSON response: {err}") from err

    # -- static info ---------------------------------------------------------

    async def get_version(self) -> str:
        version, premium, meta = await self.get_version_info()
        self.premium = premium
        self.meta = meta
        return version

    async def get_version_info(self) -> tuple[str, bool, bool]:
        """Return (version, premium, meta) and remember the build flavour.

        ``premium``/``meta`` are what sing-box and its forks use to advertise
        the extra clash-API surface. Upstream builds answer
        ``{"meta": true, "premium": true}`` as well since 1.11 (the fields
        describe the *API* compatibility level, not a paid tier), so they are
        informational: the real capability probe is
        :meth:`detect_capabilities`.
        """
        data = await self._json("GET", "/version")
        if not isinstance(data, dict):
            raise ClashApiError(200, f"unexpected /version response: {type(data).__name__}")
        version = data.get("version", "")
        # "sing-box 1.14.0" -> "1.14.0" to match the gRPC GetVersion response.
        if version.startswith("sing-box "):
            version = version.removeprefix("sing-box ")
        premium = bool(data.get("premium"))
        meta = bool(data.get("meta"))
        self.premium = premium
        self.meta = meta
        return version, premium, meta

    async def detect_capabilities(self) -> None:
        """Probe the optional clash-API endpoints once, after connecting.

        Every extra here is additive: a build that answers 404 or an empty
        payload simply loses the feature and keeps working. Detection runs
        once per client because the answer cannot change without a restart of
        sing-box (and a restart is exactly when the client is rebuilt).
        """
        try:
            data = await self._json("GET", "/group")
        except (ClashApiError, TimeoutError, ConnectionError, OSError):
            data = None
        groups = data.get("proxies") if isinstance(data, dict) else None
        self.group_delay_available = bool(groups)

        try:
            rules = await self._json("GET", "/rules")
        except (ClashApiError, TimeoutError, ConnectionError, OSError):
            rules = None
        # Upstream answers {"rules": null} until the router exposes them;
        # the premium builds answer the real list.
        rule_list = rules.get("rules") if isinstance(rules, dict) else None
        self.rules_available = isinstance(rule_list, list) and bool(rule_list)
        _LOGGER.debug(
            "clash API capabilities: group_delay=%s rules=%s premium=%s",
            self.group_delay_available,
            self.rules_available,
            self.premium,
        )

    async def get_configs(self) -> tuple[list[str], str]:
        """Return (mode_list, current_mode)."""
        data = await self._json("GET", "/configs")
        if not isinstance(data, dict):
            raise ClashApiError(200, f"unexpected /configs response: {type(data).__name__}")
        return data.get("mode-list", []), data.get("mode", "")

    async def get_proxies(self) -> tuple[list[SingBoxGroup], list[SingBoxGroupItem]]:
        """Return (selectable groups, flat proxy list with last-known delays).

        Each entry of ``/proxies`` carries a ``history`` array whose newest
        element holds the last url-test delay (ms) sing-box measured for it.
        Selector/UrlTest groups with an empty history report the delay of
        their currently selected proxy instead.

        Only ``Selector`` groups are returned as switchable groups: the clash
        API rejects PUT /proxies/{group}/ for urltest and fallback groups with
        HTTP 400 "Must be a Selector" (sing-box 1.11 through testing), so
        exposing them as select entities produced entities that could never
        be changed. Their members are still reported as proxies so ping
        sensors keep working, and the group itself keeps its own ping entry.
        """
        data = await self._json("GET", "/proxies")
        if not isinstance(data, dict):
            raise ClashApiError(200, f"unexpected /proxies response: {type(data).__name__}")
        raw = data.get("proxies", {})
        if not isinstance(raw, dict):
            raise ClashApiError(200, "unexpected /proxies.proxies: not an object")

        groups: list[SingBoxGroup] = []
        proxies: list[SingBoxGroupItem] = []
        for name, info in raw.items():
            if not isinstance(info, dict):
                continue
            # "GLOBAL" is a synthetic clash-API group (Fallback over all
            # proxies) that exists in /proxies but has no backing outbound:
            # /proxies/GLOBAL/delay answers 404 and it can never be selected.
            # Skip it so no ping sensor is created for it.
            if name == "GLOBAL":
                continue
            delay, delay_time = _last_url_test_delay(info, raw)
            # A failure the bridge reported itself wins over a stale history
            # entry: sing-box only appends to history on success, so an
            # outbound that worked an hour ago and fails now would otherwise
            # keep showing the old green delay forever.
            ping = self.last_pings.get(name)
            failed = bool(ping and ping.failed)
            if ping is not None and ping.delay > 0 and not ping.failed:
                delay, delay_time = ping.delay, ping.test_time
            elif failed:
                delay, delay_time = 0, ping.test_time if ping is not None else 0
            proxies.append(
                SingBoxGroupItem(
                    tag=name,
                    type=info.get("type", ""),
                    url_test_time=delay_time,
                    url_test_delay=delay,
                    url_test_failed=failed,
                )
            )
            group_type = info.get("type", "")
            # Only Selector groups can be switched (see _SELECTABLE_GROUP_TYPES).
            # URLTest/Fallback groups still contribute their members as proxies
            # (for ping sensors), but they get no select entity.
            if group_type in _SELECTABLE_GROUP_TYPES and isinstance(info.get("all"), list):
                items = [
                    SingBoxGroupItem(tag=tag, type="", url_test_time=0, url_test_delay=0)
                    for tag in info["all"]
                    if isinstance(tag, str)
                ]
                groups.append(
                    SingBoxGroup(
                        tag=name,
                        type=group_type,
                        selectable=True,
                        selected=info.get("now", ""),
                        is_expand=False,
                        items=items,
                    )
                )
        return groups, proxies

    async def get_connections(self) -> tuple[int, int, int, int]:
        """Return (active_connections, memory, upload_total, download_total)."""
        snapshot = await self.get_connections_snapshot()
        return snapshot[:4]  # type: ignore[return-value]

    async def get_connections_snapshot(
        self,
    ) -> tuple[int, int, int, int, list[SingBoxConnection]]:
        """Return (count, memory, upload_total, download_total, connections).

        The connection list itself used to be thrown away here, which left the
        card with nothing but a count. Parsing it costs the same single
        ``GET /connections/`` round trip, so both are returned together.
        """
        data = await self._json("GET", "/connections/")
        connections, memory, upload_total, download_total = parse_connections_snapshot(data)
        return len(connections), memory, upload_total, download_total, connections

    # -- control -------------------------------------------------------------

    async def select_outbound(self, group_tag: str, outbound_tag: str) -> None:
        """Select an outbound inside a selector group.

        The tag is percent-encoded: a real subscription uses tags like
        "eu: EU2", "ru: 🇫🇮 Финляндия · XHTTP" or anything with a slash, and
        an unencoded tag either 404s (the path no longer matches) or, when it
        contains a "/", is routed to a completely different endpoint. Both
        the upstream and the premium builds accept the encoded form.
        """
        path = f"/proxies/{quote(group_tag, safe='')}/"
        await self._json("PUT", path, json_body={"name": outbound_tag})

    async def set_clash_mode(self, mode: str) -> None:
        await self._json("PUT", "/configs", json_body={"mode": mode})

    async def url_test(self, outbound_tag: str, url: str | None = None) -> PingResult:
        """Run one url-test and return its outcome instead of raising.

        Every failure mode of a real installation used to surface as an
        exception, and Home Assistant turned that into the full-screen red
        "Failed to perform the action singbox/url_test" banner:

        * ``503 An error occurred in the delay test`` - the outbound is a
          reject/block outbound (it cannot connect by definition);
        * ``404 Resource not found`` - the outbound is the synthetic
          ``GLOBAL`` group, or a tag that disappeared between two polls;
        * ``200 {"delay": 0}`` - the test ran and failed.

        A failed url-test is *data*, not an integration error: the card wants
        to paint that node red, not make the whole dashboard apologise. So
        the result is recorded on the client, kept in ``last_pings`` for the
        sensors/websocket, and returned. Only transport-level problems
        (unreachable server, wrong secret) still raise, because those are
        real failures of the integration itself.
        """
        result = await self._delay_for(outbound_tag, url)
        self.last_pings[outbound_tag] = result
        return result

    async def _delay_for(self, outbound_tag: str, url: str | None) -> PingResult:
        """Query ``/proxies/{tag}/delay`` and normalise every answer.

        Auth errors and connection errors propagate: they are not about this
        particular outbound. Everything else becomes a PingResult.
        """
        params = {
            "url": url or DEFAULT_URL_TEST_URL,
            "timeout": str(_URL_TEST_TIMEOUT_MS),
        }
        try:
            data = await self._json(
                "GET", f"/proxies/{quote(outbound_tag, safe='')}/delay", params=params
            )
        except ClashApiError as err:
            if is_auth_error(err):
                raise
            _LOGGER.debug("url test for %s failed: %s", outbound_tag, err)
            return PingResult(tag=outbound_tag, failed=True)
        if not isinstance(data, dict):
            return PingResult(tag=outbound_tag, failed=True)
        delay = data.get("delay")
        # A group answers with {member: ms} instead of {"delay": ms}. The
        # current outbound of the group is the one the user sees in the
        # header, so its delay is the group's delay.
        if not isinstance(delay, int) or isinstance(delay, bool):
            members = parse_group_delay(data)
            if not members:
                return PingResult(tag=outbound_tag, failed=True)
            # Failed members are reported as 0 by the server, so only the
            # positive delays are real measurements. The best of them is what
            # a url-test/fallback group would route to, which is what the
            # group's ping means. Taking max() here reported the *worst* node
            # of the group (a 176 ms member showed as "820 ms" in the card).
            best = _best_delay(members.values())
            if best <= 0:
                return PingResult(tag=outbound_tag, failed=True)
            return PingResult(tag=outbound_tag, delay=best, test_time=_now_ms())
        if delay <= 0:
            return PingResult(tag=outbound_tag, failed=True)
        return PingResult(tag=outbound_tag, delay=delay, test_time=_now_ms())

    async def url_test_many(self, tags: list[str], url: str | None = None) -> dict[str, PingResult]:
        """Test several outbounds, using the group batch endpoint when it exists.

        ``GET /group/{tag}/delay`` returns the delay of every member of a group
        in one round trip, which is exactly what the card's "test this group"
        button needs (testing the group tag itself only refreshes the currently
        selected member). It exists in upstream 1.14.4 and in the premium
        builds, but answers 404 for leaf outbounds, for ``GLOBAL`` and for the
        reject outbounds, so anything it cannot answer is retried per proxy.
        """
        results: dict[str, PingResult] = {}
        remaining: list[str] = []
        for tag in tags:
            if is_testable_proxy(tag, None):
                remaining.append(tag)
        if self.group_delay_available and remaining:
            for tag in list(remaining):
                members = await self._group_delay(tag, url)
                if not members:
                    continue
                remaining.remove(tag)
                results[tag] = PingResult(
                    tag=tag, delay=_best_delay(members.values()), test_time=_now_ms()
                )
                for member, delay in members.items():
                    if member == tag:
                        continue
                    results.setdefault(
                        member,
                        PingResult(
                            tag=member,
                            delay=delay,
                            failed=delay <= 0,
                            test_time=_now_ms(),
                        ),
                    )
        # Per-proxy pass for whatever the batch endpoint did not cover.
        for tag in remaining:
            results[tag] = await self._delay_for(tag, url)
        for tag, ping in results.items():
            self.last_pings[tag] = ping
        return results

    async def _group_delay(self, group_tag: str, url: str | None = None) -> dict[str, int]:
        """Batch-test a group; empty dict when this build cannot do it.

        The URL defaults for the same reason as on the per-proxy path: this
        is the only entry point the card and the service use to refresh a
        whole group, and requiring the caller to pass a URL that almost always
        is DEFAULT_URL_TEST_URL was a needless foot-gun (calling it without
        one raised TypeError, which is not an API answer at all).
        """
        try:
            data = await self._json(
                "GET",
                f"/group/{quote(group_tag, safe='')}/delay",
                params={"url": url or DEFAULT_URL_TEST_URL, "timeout": str(_URL_TEST_TIMEOUT_MS)},
            )
        except ClashApiError as err:
            if is_auth_error(err):
                raise
            return {}
        return parse_group_delay(data)

    # -- optional / premium endpoints ---------------------------------------

    async def reload_config(self, force: bool = True) -> None:
        """Ask the server to re-apply its configuration.

        The route is PUT /configs: the clash-API router mounts exactly GET,
        PUT and PATCH on /configs (experimental/clashapi/configs.go), so POST
        is answered with 405 by *every* build - upstream and premium alike.
        The previous version posted there and therefore reported "not
        supported" on a server that does implement the route.

        What the route does depends on the build. In upstream sing-box
        updateConfigs is a deliberate no-op that answers 204
        (render.NoContent, no body read, no reload), and both 1.14.4 and
        1.14.4-pdk behave exactly like that: the request succeeds, yet an
        outbound added to the config file does not appear afterwards. So this
        method reports *acceptance*, which is all the API can promise, and
        keeps the SingBoxNotSupported mapping for builds that reject the route
        outright.
        """
        try:
            await self._json(
                "PUT", "/configs", params={"force": "true"} if force else None, json_body={}
            )
        except ClashApiError as err:
            if is_auth_error(err):
                raise
            raise SingBoxNotSupported(
                f"this sing-box build does not accept a config reload ({err})"
            ) from err

    async def flush_fakeip_cache(self) -> None:
        """Drop the fake-IP cache (POST /cache/fakeip/flush, 204)."""
        await self._post_optional("/cache/fakeip/flush", "flushing the fake-IP cache")

    async def flush_dns_cache(self) -> None:
        """Drop the DNS cache (POST /cache/dns/flush)."""
        await self._post_optional("/cache/dns/flush", "flushing the DNS cache")

    async def _post_optional(self, path: str, action: str) -> None:
        try:
            await self._json("POST", path)
        except ClashApiError as err:
            # A rejected secret is not "this build lacks the feature": reporting
            # it as SingBoxNotSupported turned a reauth-worthy 401 into a
            # harmless capability message, so the entry never re-authenticated.
            if is_auth_error(err):
                raise
            raise SingBoxNotSupported(
                f"{action} is not supported by this sing-box build ({err})"
            ) from err

    async def get_rules(self) -> list[dict[str, str]]:
        """Return the route rules; empty on builds that do not expose them.

        Upstream 1.14.4 answers ``{"rules": null}`` and premium builds answer
        the real list, so the empty case is normal and must not be an error.
        """
        try:
            data = await self._json("GET", "/rules")
        except ClashApiError as err:
            # 404 on a build without the endpoint is normal ("no rules to
            # show"), but 401/403 means the entry lost access: swallowing that
            # hid an expired secret from the reauth flow.
            if is_auth_error(err):
                raise
            return []
        raw = data.get("rules") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            return []
        rules: list[dict[str, str]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            rules.append(
                {
                    "type": str(entry.get("type", "")),
                    "payload": str(entry.get("payload", "")),
                    "proxy": str(entry.get("proxy", "")),
                }
            )
        return rules

    async def dns_query(self, name: str, record_type: str = "A") -> dict[str, Any]:
        """Resolve a name through sing-box's own DNS (premium endpoint).

        A 400 (the server rejected the record type) propagates unchanged: it is
        the caller's mistake, not a missing feature. Only a missing route turns
        into SingBoxNotSupported.
        """
        try:
            data = await self._json(
                "GET", "/dns/query", params={"name": name, "type": record_type.upper()}
            )
        except ClashApiError as err:
            if is_auth_error(err) or err.status == 400:
                raise
            raise SingBoxNotSupported(
                f"DNS queries are not supported by this sing-box build ({err})"
            ) from err
        return data if isinstance(data, dict) else {}

    async def set_group_expand(self, group_tag: str, is_expand: bool) -> None:
        raise SingBoxNotSupported("expanding a group is not supported by the clash API backend")

    async def close_connection(self, connection_id: str) -> None:
        """Close one connection by id.

        Encoded for the same reason as the proxy tags: the id is opaque server
        text, and a "/" in it would silently address a different endpoint.
        """
        await self._json("DELETE", f"/connections/{quote(connection_id, safe='')}")

    async def close_all_connections(self) -> None:
        await self._json("DELETE", "/connections/")

    # -- streams -------------------------------------------------------------

    async def _open_ws(self, path: str) -> aiohttp.ClientWebSocketResponse:
        session = await self._request_session()
        try:
            ws = await session.ws_connect(self._url(path), headers=self._headers(), timeout=10)
        except aiohttp.ClientError as err:
            raise ConnectionError(f"cannot open clash API stream {path}: {err}") from err
        self._ws.append(ws)
        return ws

    async def _ws_receive(self, ws: aiohttp.ClientWebSocketResponse):
        """Receive one WebSocket frame with a bounded wait.

        The idle timeout is enforced by aiohttp itself instead of an extra
        asyncio.wait_for() wrapper: the wrapper allocated a TimerHandle and a
        Context on *every* frame, and it could never fire once the event loop
        was starved by the busy loop described in traffic_stream().
        """
        if _WS_RECEIVE_TIMEOUT_ARG:
            return await ws.receive(timeout=_WS_IDLE_TIMEOUT)
        return await asyncio.wait_for(ws.receive(), timeout=_WS_IDLE_TIMEOUT)

    async def traffic_stream(self) -> AsyncIterator[tuple[int, int]]:
        """Yield (up, down) byte deltas per second from the WS /traffic stream.

        Any frame that is not TEXT terminates the stream. aiohttp answers
        WSMsgType.CLOSED when the TCP transport is aborted without a close
        frame (exactly what happens when sing-box dies during HA shutdown);
        receive() then returns immediately from the dead socket, so treating
        non-TEXT frames as 'continue' spun this loop at ~170 000 iterations/s,
        allocating millions of asyncio.wait_for timers until the kernel
        OOM-killed Home Assistant. Re-entering receive() on a closed socket is
        never useful, so every non-TEXT frame is terminal here and the
        coordinator reconnects through its own backoff.
        """
        ws = await self._open_ws("/traffic")
        try:
            while True:
                try:
                    msg = await self._ws_receive(ws)
                except TimeoutError as err:
                    raise ConnectionError("traffic stream idle timeout") from err
                if msg.type is not aiohttp.WSMsgType.TEXT:
                    # CLOSE / CLOSING / CLOSED / ERROR / BINARY: all terminal.
                    raise ConnectionError(
                        f"traffic stream ended: {getattr(msg.type, 'name', msg.type)}"
                    )
                try:
                    data = json.loads(msg.data)
                except ValueError as err:
                    raise ClashApiError(200, f"invalid traffic frame: {err}") from err
                if not isinstance(data, dict):
                    raise ClashApiError(200, "invalid traffic frame: not an object")
                yield int(data.get("up", 0)), int(data.get("down", 0))
        finally:
            if ws in self._ws:
                self._ws.remove(ws)
            try:
                await asyncio.wait_for(ws.close(), timeout=2)
            except (TimeoutError, ConnectionError, OSError):
                pass
