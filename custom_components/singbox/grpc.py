"""Minimal protobuf and gRPC-Web client for the sing-box API service.

The sing-box ``api`` service (sing-box >= 1.14.0) is a gRPC server that also
accepts gRPC-Web requests over plain HTTP, so this integration needs no
third-party gRPC/protobuf dependencies — only aiohttp, which ships with
Home Assistant.

Wire details (all verified against sing-box 1.14.0):

* RPC path: ``POST /daemon.StartedService/<Method>``
* Headers: ``Content-Type: application/grpc-web+proto`` and, when a secret is
  configured, ``Authorization: Bearer <secret>``.
* Request/response bodies are gRPC-Web framed: 1 byte of flags (0x80 marks a
  trailer frame) + 4 byte big-endian length + payload.
* gRPC status is returned either in a trailing frame (``grpc-status: N``) or,
  for immediate failures, as ``grpc-status`` / ``grpc-message`` HTTP headers
  with an empty body (trailers-only response).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator

import aiohttp

_LOGGER = logging.getLogger(__package__)

GRPC_WEB_CONTENT_TYPE = "application/grpc-web+proto"

GRPC_STATUS_OK = 0
GRPC_STATUS_NOT_FOUND = 5
GRPC_STATUS_UNIMPLEMENTED = 12
GRPC_STATUS_UNAUTHENTICATED = 16

# The stream of Status messages is pushed every second by default; if no bytes
# arrive for this long the stream is considered dead and gets re-established.
_STREAM_IDLE_TIMEOUT = 45.0

_SERVICE_PATH = "/daemon.StartedService/"


class GrpcError(Exception):
    """A gRPC call failed with a non-OK status code."""

    def __init__(self, status: int, message: str | None = None) -> None:
        super().__init__(message or f"gRPC status {status}")
        self.status = status


# ---------------------------------------------------------------------------
# protobuf wire format
# ---------------------------------------------------------------------------

def _varint(value: int) -> bytes:
    out = bytearray()
    while value > 0x7F:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7


def _field_varint(num: int, value: int) -> bytes:
    return _varint((num << 3) | 0) + _varint(value)


def _field_bytes(num: int, value: bytes) -> bytes:
    return _varint((num << 3) | 2) + _varint(len(value)) + value


def _field_bool(num: int, value: bool) -> bytes:
    return _field_varint(num, 1 if value else 0)


def empty_message() -> bytes:
    return b""


def subscribe_status_request(interval_ns: int) -> bytes:
    return _field_varint(1, interval_ns)


def select_outbound_request(group_tag: str, outbound_tag: str) -> bytes:
    return _field_bytes(1, group_tag.encode()) + _field_bytes(2, outbound_tag.encode())


def set_group_expand_request(group_tag: str, is_expand: bool) -> bytes:
    return _field_bytes(1, group_tag.encode()) + _field_bool(2, is_expand)


def url_test_request(outbound_tag: str) -> bytes:
    return _field_bytes(1, outbound_tag.encode())


def close_connection_request(connection_id: str) -> bytes:
    return _field_bytes(1, connection_id.encode())


def clash_mode_request(mode: str) -> bytes:
    return _field_bytes(3, mode.encode())


def decode_fields(data: bytes) -> dict[int, list[int | bytes]]:
    """Decode a protobuf message into {field_number: [values]}."""
    fields: dict[int, list[int | bytes]] = {}
    pos = 0
    while pos < len(data):
        key, pos = _read_varint(data, pos)
        num, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _read_varint(data, pos)
        elif wire == 2:
            length, pos = _read_varint(data, pos)
            value = data[pos : pos + length]
            pos += length
        elif wire == 5:
            value = data[pos : pos + 4]
            pos += 4
        elif wire == 1:
            value = data[pos : pos + 8]
            pos += 8
        else:
            raise ValueError(f"unsupported protobuf wire type {wire}")
        fields.setdefault(num, []).append(value)
    return fields


def _str(fields: dict[int, list[int | bytes]], num: int) -> str:
    value = fields.get(num)
    if not value or not isinstance(value[0], bytes):
        return ""
    return value[0].decode()


def _int(fields: dict[int, list[int | bytes]], num: int) -> int:
    value = fields.get(num)
    if not value:
        return 0
    if isinstance(value[0], int):
        return value[0]
    return int.from_bytes(value[0], "little")


def _bool(fields: dict[int, list[int | bytes]], num: int) -> bool:
    return _int(fields, num) != 0


def _str_list(fields: dict[int, list[int | bytes]], num: int) -> list[str]:
    return [v.decode() for v in fields.get(num, []) if isinstance(v, bytes)]


# ---------------------------------------------------------------------------
# data model
# ---------------------------------------------------------------------------

@dataclass
class SingBoxGroupItem:
    tag: str
    type: str
    url_test_time: int
    url_test_delay: int


@dataclass
class SingBoxGroup:
    tag: str
    type: str
    selectable: bool
    selected: str
    is_expand: bool
    items: list[SingBoxGroupItem] = field(default_factory=list)


@dataclass
class SingBoxStatus:
    version: str | None = None
    api_version: int | None = None
    started_at: int | None = None
    memory: int | None = None
    goroutines: int | None = None
    connections_in: int | None = None
    connections_out: int | None = None
    traffic_available: bool | None = None
    uplink: int | None = None
    downlink: int | None = None
    uplink_total: int | None = None
    downlink_total: int | None = None
    groups: list[SingBoxGroup] = field(default_factory=list)
    clash_mode_list: list[str] | None = None
    clash_mode: str | None = None


# ---------------------------------------------------------------------------
# gRPC-Web framing
# ---------------------------------------------------------------------------

def _data_frame(payload: bytes) -> bytes:
    return b"\x00" + len(payload).to_bytes(4, "big") + payload


def _take_frame(buf: bytearray) -> tuple[bool, bytes] | None:
    """Pop one frame from the buffer head, or None when incomplete."""
    if len(buf) < 5:
        return None
    flags = buf[0]
    length = int.from_bytes(buf[1:5], "big")
    if len(buf) < 5 + length:
        return None
    payload = bytes(buf[5 : 5 + length])
    del buf[: 5 + length]
    return bool(flags & 0x80), payload


def _parse_trailer(payload: bytes) -> tuple[int, str | None]:
    status = GRPC_STATUS_OK
    message: str | None = None
    for line in payload.decode(errors="replace").splitlines():
        if line.startswith("grpc-status:"):
            status = int(line.split(":", 1)[1].strip())
        elif line.startswith("grpc-message:"):
            message = line.split(":", 1)[1].strip()
    return status, message


def _parse_status_response(headers, body: bytes) -> tuple[int, str | None]:
    """Extract the gRPC status from a response (headers or trailer frame)."""
    header_status = headers.get("grpc-status")
    if header_status is not None:
        return int(header_status), headers.get("grpc-message")
    for is_trailer, payload in _iter_frames(body):
        if is_trailer:
            return _parse_trailer(payload)
    return GRPC_STATUS_OK, None


def _iter_frames(body: bytes) -> AsyncIterator[tuple[bool, bytes]]:
    buf = bytearray(body)
    while True:
        frame = _take_frame(buf)
        if frame is None:
            return
        yield frame


# ---------------------------------------------------------------------------
# client
# ---------------------------------------------------------------------------

class SingBoxClient:
    """Async client for the sing-box ``api`` service over gRPC-Web."""

    def __init__(
        self,
        host: str,
        port: int,
        secret: str = "",
        use_tls: bool = False,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        scheme = "https" if use_tls else "http"
        self._base_url = f"{scheme}://{host}:{port}"
        self._secret = secret
        self._session = session
        self._own_session = session is None

    def _url(self, method: str) -> str:
        return f"{self._base_url}{_SERVICE_PATH}{method}"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": GRPC_WEB_CONTENT_TYPE,
            "X-Grpc-Web": "1",
        }
        if self._secret:
            headers["Authorization"] = f"Bearer {self._secret}"
        return headers

    async def _request_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._own_session and self._session is not None:
            await self._session.close()
            self._session = None

    async def unary(self, method: str, request: bytes) -> bytes | None:
        """Call a unary RPC; return the response message payload (or None)."""
        session = await self._request_session()
        try:
            async with session.post(
                self._url(method),
                data=_data_frame(request),
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                body = await resp.read()
                if resp.status != 200:
                    # A non-gRPC server (e.g. a clash_api-only sing-box) answers
                    # 404 for RPC paths without a grpc-status header.
                    raise GrpcError(
                        GRPC_STATUS_UNIMPLEMENTED,
                        f"RPC {method} failed (HTTP {resp.status})",
                    )
                status, message = _parse_status_response(resp.headers, body)
        except aiohttp.ClientError as err:
            raise ConnectionError(f"cannot reach sing-box API at {self._base_url}: {err}") from err
        if status != GRPC_STATUS_OK:
            raise GrpcError(status, message or f"RPC {method} failed")
        messages = [
            payload for is_trailer, payload in _iter_frames(body) if not is_trailer
        ]
        return messages[0] if messages else None

    async def stream(self, method: str, request: bytes) -> AsyncIterator[bytes]:
        """Server-streaming RPC: yields message payloads as they arrive."""
        session = await self._request_session()
        resp = await session.post(
            self._url(method),
            data=_data_frame(request),
            headers=self._headers(),
        )
        try:
            if resp.status != 200:
                body = await resp.read()
                status, message = _parse_status_response(resp.headers, body)
                raise GrpcError(status, message or f"RPC {method} failed (HTTP {resp.status})")
            buf = bytearray()
            while True:
                try:
                    chunk = await asyncio.wait_for(
                        resp.content.read(4096), timeout=_STREAM_IDLE_TIMEOUT
                    )
                except asyncio.TimeoutError as err:
                    raise ConnectionError(f"stream {method} idle timeout") from err
                if not chunk:
                    break
                buf.extend(chunk)
                while True:
                    frame = _take_frame(buf)
                    if frame is None:
                        break
                    is_trailer, payload = frame
                    if is_trailer:
                        status, message = _parse_trailer(payload)
                        if status != GRPC_STATUS_OK:
                            raise GrpcError(status, message or f"RPC {method} failed")
                        return
                    yield payload
            raise ConnectionError(f"stream {method} closed by server")
        finally:
            resp.release()

    # -- individual RPCs ----------------------------------------------------

    async def get_version(self) -> tuple[str, int]:
        payload = await self.unary("GetVersion", empty_message())
        fields = decode_fields(payload or b"")
        return _str(fields, 1), _int(fields, 2)

    async def get_started_at(self) -> int:
        payload = await self.unary("GetStartedAt", empty_message())
        return _int(decode_fields(payload or b""), 1)

    async def get_clash_mode_status(self) -> tuple[list[str], str]:
        """Raises GrpcError(5) when the clash API is not enabled."""
        payload = await self.unary("GetClashModeStatus", empty_message())
        fields = decode_fields(payload or b"")
        return _str_list(fields, 1), _str(fields, 2)

    async def set_clash_mode(self, mode: str) -> None:
        await self.unary("SetClashMode", clash_mode_request(mode))

    async def subscribe_status(self, interval_ns: int) -> AsyncIterator[dict[int, list[int | bytes]]]:
        async for payload in self.stream("SubscribeStatus", subscribe_status_request(interval_ns)):
            yield decode_fields(payload)

    async def subscribe_groups(self) -> AsyncIterator[list[SingBoxGroup]]:
        async for payload in self.stream("SubscribeGroups", empty_message()):
            yield _parse_groups(payload)

    async def select_outbound(self, group_tag: str, outbound_tag: str) -> None:
        await self.unary("SelectOutbound", select_outbound_request(group_tag, outbound_tag))

    async def set_group_expand(self, group_tag: str, is_expand: bool) -> None:
        await self.unary("SetGroupExpand", set_group_expand_request(group_tag, is_expand))

    async def url_test(self, outbound_tag: str) -> None:
        await self.unary("URLTest", url_test_request(outbound_tag))

    async def close_connection(self, connection_id: str) -> None:
        await self.unary("CloseConnection", close_connection_request(connection_id))

    async def close_all_connections(self) -> None:
        await self.unary("CloseAllConnections", empty_message())


def _parse_groups(payload: bytes) -> list[SingBoxGroup]:
    groups: list[SingBoxGroup] = []
    for raw in decode_fields(payload).get(1, []):
        if not isinstance(raw, bytes):
            continue
        group_fields = decode_fields(raw)
        items = [
            SingBoxGroupItem(
                tag=_str(item, 1),
                type=_str(item, 2),
                url_test_time=_int(item, 3),
                url_test_delay=_int(item, 4),
            )
            for item in (
                decode_fields(raw_item)
                for raw_item in group_fields.get(6, [])
                if isinstance(raw_item, bytes)
            )
        ]
        groups.append(
            SingBoxGroup(
                tag=_str(group_fields, 1),
                type=_str(group_fields, 2),
                selectable=_bool(group_fields, 3),
                selected=_str(group_fields, 4),
                is_expand=_bool(group_fields, 5),
                items=items,
            )
        )
    return groups
