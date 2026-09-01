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

Only aiohttp is used, which ships with Home Assistant.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import aiohttp

from .grpc import SingBoxGroup, SingBoxGroupItem

_LOGGER = logging.getLogger(__package__)

# URL used when the url_test service is invoked without an explicit target.
DEFAULT_URL_TEST_URL = "https://www.gstatic.com/generate_204"
_URL_TEST_TIMEOUT_MS = 5000
# If no WebSocket frame arrives for this long the stream is considered dead.
_WS_IDLE_TIMEOUT = 45.0
# The polling loop refreshes groups/config/connection totals on this cadence.
POLL_INTERVAL_SECONDS = 5


def _last_url_test_delay(info: dict, all_proxies: dict) -> tuple[int, int]:
    """Return (delay_ms, time_ms) of the newest history entry of a proxy.

    Falls back to the currently selected proxy for groups whose own history
    is empty (Selector groups never record one; UrlTest groups do).
    """
    history = info.get("history")
    if isinstance(history, list):
        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            delay = entry.get("delay")
            if isinstance(delay, int) and delay > 0:
                tested_at = entry.get("time")
                return delay, tested_at if isinstance(tested_at, int) else 0
    now = info.get("now")
    if isinstance(now, str):
        target = all_proxies.get(now)
        if isinstance(target, dict) and target is not info:
            delay, tested_at = _last_url_test_delay(target, all_proxies)
            if delay:
                return delay, tested_at
    return 0, 0


class ClashApiError(Exception):
    """A clash API call failed with a non-success status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"clash API HTTP {status}: {message}")
        self.status = status


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
            except (asyncio.TimeoutError, ConnectionError, OSError):
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
        data = await self._json("GET", "/version")
        if not isinstance(data, dict):
            raise ClashApiError(200, f"unexpected /version response: {type(data).__name__}")
        version = data.get("version", "")
        # "sing-box 1.14.0" -> "1.14.0" to match the gRPC GetVersion response.
        if version.startswith("sing-box "):
            version = version.removeprefix("sing-box ")
        return version

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
            delay, delay_time = _last_url_test_delay(info, raw)
            proxies.append(
                SingBoxGroupItem(
                    tag=name,
                    type=info.get("type", ""),
                    url_test_time=delay_time,
                    url_test_delay=delay,
                )
            )
            if (
                info.get("type") == "Selector"
                and isinstance(info.get("all"), list)
            ):
                items = [
                    SingBoxGroupItem(tag=tag, type="", url_test_time=0, url_test_delay=0)
                    for tag in info["all"]
                    if isinstance(tag, str)
                ]
                groups.append(
                    SingBoxGroup(
                        tag=name,
                        type="Selector",
                        selectable=True,
                        selected=info.get("now", ""),
                        is_expand=False,
                        items=items,
                    )
                )
        return groups, proxies

    async def get_connections(self) -> tuple[int, int, int, int]:
        """Return (active_connections, memory, upload_total, download_total)."""
        data = await self._json("GET", "/connections/")
        if not isinstance(data, dict):
            raise ClashApiError(200, f"unexpected /connections response: {type(data).__name__}")
        connections = data.get("connections", [])
        return (
            len(connections) if isinstance(connections, list) else 0,
            data.get("memory", 0),
            data.get("uploadTotal", 0),
            data.get("downloadTotal", 0),
        )

    # -- control -------------------------------------------------------------

    async def select_outbound(self, group_tag: str, outbound_tag: str) -> None:
        await self._json("PUT", f"/proxies/{group_tag}/", json_body={"name": outbound_tag})

    async def set_clash_mode(self, mode: str) -> None:
        await self._json("PUT", "/configs", json_body={"mode": mode})

    async def url_test(self, outbound_tag: str, url: str | None = None) -> None:
        await self._json(
            "GET",
            f"/proxies/{outbound_tag}/delay",
            params={
                "url": url or DEFAULT_URL_TEST_URL,
                "timeout": str(_URL_TEST_TIMEOUT_MS),
            },
        )

    async def close_connection(self, connection_id: str) -> None:
        await self._json("DELETE", f"/connections/{connection_id}")

    async def close_all_connections(self) -> None:
        await self._json("DELETE", "/connections/")

    # -- streams -------------------------------------------------------------

    async def _open_ws(self, path: str) -> aiohttp.ClientWebSocketResponse:
        session = await self._request_session()
        try:
            ws = await session.ws_connect(
                self._url(path), headers=self._headers(), timeout=10
            )
        except aiohttp.ClientError as err:
            raise ConnectionError(
                f"cannot open clash API stream {path}: {err}"
            ) from err
        self._ws.append(ws)
        return ws

    async def traffic_stream(self) -> AsyncIterator[tuple[int, int]]:
        """Yield (up, down) byte deltas per second from the WS /traffic stream."""
        ws = await self._open_ws("/traffic")
        try:
            while True:
                try:
                    msg = await asyncio.wait_for(ws.receive(), timeout=_WS_IDLE_TIMEOUT)
                except asyncio.TimeoutError as err:
                    raise ConnectionError("traffic stream idle timeout") from err
                if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.ERROR):
                    raise ConnectionError(f"traffic stream closed: {msg.type}")
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                try:
                    data = json.loads(msg.data)
                except ValueError as err:
                    raise ClashApiError(200, f"invalid traffic frame: {err}") from err
                yield int(data.get("up", 0)), int(data.get("down", 0))
        finally:
            if ws in self._ws:
                self._ws.remove(ws)
            try:
                await asyncio.wait_for(ws.close(), timeout=2)
            except (asyncio.TimeoutError, ConnectionError, OSError):
                pass
