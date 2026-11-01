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

import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .errors import SingBoxError

_LOGGER = logging.getLogger(__package__)

GRPC_WEB_CONTENT_TYPE = "application/grpc-web+proto"

GRPC_STATUS_OK = 0
GRPC_STATUS_UNKNOWN = 2
GRPC_STATUS_NOT_FOUND = 5
GRPC_STATUS_UNIMPLEMENTED = 12
GRPC_STATUS_UNAUTHENTICATED = 16

# The stream of Status messages is pushed every second by default; if no bytes
# arrive for this long the stream is considered dead and gets re-established.
_STREAM_IDLE_TIMEOUT = 45.0

_SERVICE_PATH = "/daemon.StartedService/"


class GrpcError(SingBoxError):
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
        if pos >= len(data):
            raise ValueError("truncated protobuf varint")
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, pos
        shift += 7
        if shift >= 64:
            raise ValueError("protobuf varint is too long")


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


def subscribe_connections_request(interval_ns: int) -> bytes:
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
    """Decode a protobuf message into {field_number: [values]}.

    Truncated messages raise ValueError: a short length-delimited field used to
    be silently sliced (b"\x0a\x05ab" decoded as "ab") and a truncated varint
    raised a bare IndexError that bypassed the callers' malformed-frame
    handling.
    """
    fields: dict[int, list[int | bytes]] = {}
    pos = 0
    while pos < len(data):
        key, pos = _read_varint(data, pos)
        num, wire = key >> 3, key & 7
        if wire == 0:
            value, pos = _read_varint(data, pos)
        elif wire == 2:
            length, pos = _read_varint(data, pos)
            if pos + length > len(data):
                raise ValueError(
                    f"truncated protobuf field {num}: need {length} bytes, "
                    f"{len(data) - pos} available"
                )
            value = data[pos : pos + length]
            pos += length
        elif wire == 5:
            if pos + 4 > len(data):
                raise ValueError(f"truncated protobuf field {num}")
            value = data[pos : pos + 4]
            pos += 4
        elif wire == 1:
            if pos + 8 > len(data):
                raise ValueError(f"truncated protobuf field {num}")
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


def _int32(fields: dict[int, list[int | bytes]], num: int) -> int:
    """Read a proto3 ``int32`` field, restoring the sign of negative values.

    Negative int32 values are sign-extended to 64 bits on the wire (sing-box
    sends ``userId = -1`` for "unknown"), so the unsigned varint decoder would
    report 18446744073709551615 instead of -1. Encoders that emit only the low
    32 bits are handled too.
    """
    value = _int(fields, num)
    if value >= 1 << 63:
        return value - (1 << 64)
    if 1 << 31 <= value <= 0xFFFFFFFF:
        return value - (1 << 32)
    return value


def _bool(fields: dict[int, list[int | bytes]], num: int) -> bool:
    return _int(fields, num) != 0


def _str_list(fields: dict[int, list[int | bytes]], num: int) -> list[str]:
    return [v.decode() for v in fields.get(num, []) if isinstance(v, bytes)]


# ---------------------------------------------------------------------------
# connections
# ---------------------------------------------------------------------------

# Second field of ``ConnectionEvent`` (``ConnectionEventType``). The proto
# encodes the two "gone" cases as a single CONNECTION_EVENT_CLOSED, but both
# the clash snapshot and older builds may report a closed connection inline.
CONNECTION_EVENT_NEW = 0
CONNECTION_EVENT_UPDATE = 1
CONNECTION_EVENT_CLOSED = 2


@dataclass
class SingBoxConnection:
    """One tracked connection, as reported by either backend.

    This is the single, backend-neutral shape used by the coordinator and by
    the ``singbox/connections`` websocket command, so the bundled card never
    has to care which API produced it. Field names are stable API: the
    websocket command serialises them as-is with :meth:`SingBoxConnection.as_dict`.
    """

    # Stable sing-box connection id (a UUID string).
    id: str = ""
    # "tcp" or "udp".
    network: str = ""
    # Sniffed protocol (e.g. "https", "tls"), empty when not sniffed.
    protocol: str = ""
    # "1.2.3.4:12345" style source and destination endpoints.
    source: str = ""
    destination: str = ""
    # Domain (or destination FQDN) the connection was made to.
    host: str = ""
    # Matched route rule and the outbound that handled the connection.
    rule: str = ""
    outbound: str = ""
    # Outbound chain, outermost group first (["proxy", "hk"]).
    chain: list[str] = field(default_factory=list)
    # Process name/path that opened the connection, empty when unknown.
    process: str = ""
    # Traffic rates of the last interval, in bytes per second.
    upload: int = 0
    download: int = 0
    # Cumulative traffic of the connection, in bytes.
    upload_total: int = 0
    download_total: int = 0
    # Creation time, epoch milliseconds.
    created_at: int = 0

    def as_dict(self) -> dict[str, Any]:
        """Return the flat, snake_case payload used by the websocket API."""
        return {
            "id": self.id,
            "network": self.network,
            "protocol": self.protocol,
            "source": self.source,
            "destination": self.destination,
            "host": self.host,
            "rule": self.rule,
            "outbound": self.outbound,
            "chain": list(self.chain),
            "process": self.process,
            "upload": self.upload,
            "download": self.download,
            "upload_total": self.upload_total,
            "download_total": self.download_total,
            "created_at": self.created_at,
        }


@dataclass
class SingBoxConnectionUpdate:
    """One ``ConnectionEvents`` frame, decoded.

    ``reset`` means the payload is the complete set of known connections and
    whatever the coordinator holds must be dropped first. Otherwise every
    event is a delta: NEW/UPDATE carry the current snapshot of a connection,
    CLOSED only carries its id.
    """

    connections: list[SingBoxConnection] = field(default_factory=list)
    closed_ids: list[str] = field(default_factory=list)
    reset: bool = False


def _parse_process_info(raw: bytes) -> str:
    """Render a ``ProcessInfo`` as the single string the card displays.

    Matches what the clash snapshot does: prefer the executable path, fall
    back to the first Android package name, and append the user name/id when
    sing-box knows one.
    """
    process = decode_fields(raw)
    path = _str(process, 4)
    if not path:
        packages = _str_list(process, 5)
        path = packages[0] if packages else ""
    user = _str(process, 3)
    if not user:
        user_id = _int32(process, 2)
        user = str(user_id) if user_id != -1 else ""
    if path and user:
        return f"{path} ({user})"
    return path


def _parse_connection(raw: bytes) -> SingBoxConnection:
    fields = decode_fields(raw)
    process = ""
    for raw_process in fields.get(22, []):
        if isinstance(raw_process, bytes):
            process = _parse_process_info(raw_process)
    return SingBoxConnection(
        id=_str(fields, 1),
        network=_str(fields, 5),
        protocol=_str(fields, 9),
        source=_str(fields, 6),
        destination=_str(fields, 7),
        host=_str(fields, 8),
        rule=_str(fields, 18),
        outbound=_str(fields, 19),
        chain=_str_list(fields, 21),
        process=process,
        upload_total=_int(fields, 16),
        download_total=_int(fields, 17),
        created_at=_int(fields, 12),
    )


def parse_connection_events(payload: bytes) -> SingBoxConnectionUpdate:
    """Decode a ``ConnectionEvents`` message.

    ``ConnectionEvents{ repeated ConnectionEvent events = 1; bool reset = 2; }``
    and ``ConnectionEvent{ type = 1; id = 2; connection = 3; uplinkDelta = 4;
    downlinkDelta = 5; closedAt = 6; }``.

    The deltas and the closing timestamp are dropped on purpose: the card
    needs the byte counters and the two endpoints, and the deltas of a
    subscription are only meaningful between two consecutive frames of the
    same stream.
    """
    fields = decode_fields(payload)
    update = SingBoxConnectionUpdate(reset=_bool(fields, 2))
    for raw_event in fields.get(1, []):
        if not isinstance(raw_event, bytes):
            continue
        event = decode_fields(raw_event)
        event_id = _str(event, 2)
        raw_connection = None
        for candidate in event.get(3, []):
            if isinstance(candidate, bytes):
                raw_connection = candidate
        if _int(event, 1) == CONNECTION_EVENT_CLOSED:
            # A closed event may still carry the final snapshot of the
            # connection; the id is what matters.
            if event_id:
                update.closed_ids.append(event_id)
            continue
        if raw_connection is None:
            if not event_id:
                continue
            # UPDATE without a snapshot (only deltas): nothing to store, the
            # coordinator already has the connection from its NEW event.
            continue
        connection = _parse_connection(raw_connection)
        if not connection.id:
            connection.id = event_id
        update.connections.append(connection)
    return update


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
    # Flat, de-duplicated list of all known proxies (group members) with the
    # last url-test delay known to sing-box.
    proxies: list[SingBoxGroupItem] = field(default_factory=list)
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
        name, _, raw = line.partition(":")
        value = raw.strip()
        if name == "grpc-status":
            try:
                status = int(value)
            except ValueError:
                # Unparsable status (e.g. a non-gRPC server answering on the
                # RPC path): report it as an unknown gRPC failure instead of
                # raising a ValueError that kills the stream task.
                status = GRPC_STATUS_UNKNOWN
                message = message or f"invalid grpc-status: {value!r}"
        elif name == "grpc-message":
            message = value
    return status, message


def _parse_status_response(headers, body: bytes) -> tuple[int, str | None]:
    """Extract the gRPC status from a response (headers or trailer frame)."""
    header_status = headers.get("grpc-status")
    if header_status is not None:
        try:
            return int(header_status), headers.get("grpc-message")
        except ValueError:
            return (
                GRPC_STATUS_UNKNOWN,
                f"invalid grpc-status header: {header_status!r}",
            )
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
        self._base_url = f"{scheme}://{host}:{int(port)}"
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
        messages = [payload for is_trailer, payload in _iter_frames(body) if not is_trailer]
        return messages[0] if messages else None

    async def stream(self, method: str, request: bytes) -> AsyncIterator[bytes]:
        """Server-streaming RPC: yields message payloads as they arrive.

        The idle timeout is enforced by aiohttp (sock_read) instead of an
        asyncio.wait_for() around every read(): the wrapper allocated a
        TimerHandle and a Context per chunk - the same allocation pattern that
        caused the WebSocket OOM - and the session-wide default total timeout
        silently capped the whole stream at 5 minutes anyway.
        """
        session = await self._request_session()
        try:
            resp = await session.post(
                self._url(method),
                data=_data_frame(request),
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=None, sock_read=_STREAM_IDLE_TIMEOUT),
            )
        except aiohttp.ClientError as err:
            raise ConnectionError(f"cannot reach sing-box API at {self._base_url}: {err}") from err
        try:
            if resp.status != 200:
                body = await resp.read()
                status, message = _parse_status_response(resp.headers, body)
                raise GrpcError(status, message or f"RPC {method} failed (HTTP {resp.status})")
            buf = bytearray()
            while True:
                try:
                    chunk = await resp.content.read(4096)
                except (TimeoutError, aiohttp.ClientError) as err:
                    # sock_read fires as ServerTimeoutError (a ClientError);
                    # some aiohttp builds raise a plain TimeoutError.
                    raise ConnectionError(f"stream {method} lost: {err}") from err
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

    async def subscribe_status(
        self, interval_ns: int
    ) -> AsyncIterator[dict[int, list[int | bytes]]]:
        async for payload in self.stream("SubscribeStatus", subscribe_status_request(interval_ns)):
            yield decode_fields(payload)

    async def subscribe_groups(self) -> AsyncIterator[list[SingBoxGroup]]:
        async for payload in self.stream("SubscribeGroups", empty_message()):
            yield _parse_groups(payload)

    async def subscribe_connections(
        self, interval_ns: int
    ) -> AsyncIterator[SingBoxConnectionUpdate]:
        """Stream connection events (new/update/closed, plus reset frames).

        Only sing-box builds with connection tracking answer this RPC; the
        others return UNIMPLEMENTED ("connection tracking not available").
        """
        async for payload in self.stream(
            "SubscribeConnections", subscribe_connections_request(interval_ns)
        ):
            yield parse_connection_events(payload)

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


def flatten_proxies(groups: list[SingBoxGroup]) -> list[SingBoxGroupItem]:
    """Merge group members into a flat, de-duplicated proxy list.

    A proxy can appear in several groups; keep the entry with the freshest
    url-test result, preferring a known delay over an empty one.
    """
    merged: dict[str, SingBoxGroupItem] = {}
    for group in groups:
        for item in group.items:
            prev = merged.get(item.tag)
            if prev is None:
                merged[item.tag] = item
            elif prev.url_test_delay == 0 and item.url_test_delay > 0:
                merged[item.tag] = item
            elif item.url_test_time > prev.url_test_time:
                merged[item.tag] = item
    return list(merged.values())
