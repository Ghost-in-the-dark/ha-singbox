"""Tests for the connection list: clash snapshot, gRPC stream and websocket API."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.singbox.backend import BACKEND_CLASH, BACKEND_GRPC
from custom_components.singbox.clash import ClashApiError, parse_connections_snapshot
from custom_components.singbox.const import DOMAIN
from custom_components.singbox.coordinator import SingBoxCoordinator
from custom_components.singbox.grpc import (
    GRPC_STATUS_UNIMPLEMENTED,
    GrpcError,
    SingBoxConnection,
    SingBoxConnectionUpdate,
    _field_bytes,
    _field_varint,
    parse_connection_events,
)

from .conftest import MOCK_ENTRY_DATA

# -- protobuf helpers -------------------------------------------------------


def _message(*fields: bytes) -> bytes:
    return b"".join(fields)


def _connection_message(
    *,
    connection_id: str = "0c1d2e3f",
    network: str = "tcp",
    protocol: str = "https",
    source: str = "192.168.1.5:51234",
    destination: str = "93.184.216.34:443",
    domain: str = "example.com",
    rule: str = "geosite-example",
    outbound: str = "proxy",
    chain: tuple[str, ...] = ("proxy", "hk"),
    created_at: int = 1730000000000,
    uplink_total: int = 1000,
    downlink_total: int = 2000,
    process_path: str | None = None,
    process_user: str | None = None,
    package_names: tuple[str, ...] = (),
    process: bytes | None = None,
) -> bytes:
    fields = [
        _field_bytes(1, connection_id.encode()),
        _field_bytes(5, network.encode()),
        _field_bytes(6, source.encode()),
        _field_bytes(7, destination.encode()),
        _field_bytes(8, domain.encode()),
        _field_bytes(9, protocol.encode()),
        _field_bytes(18, rule.encode()),
        _field_bytes(19, outbound.encode()),
        *(_field_bytes(21, item.encode()) for item in chain),
        _field_varint(12, created_at),
        _field_varint(16, uplink_total),
        _field_varint(17, downlink_total),
    ]
    if process is not None:
        fields.append(_field_bytes(22, process))
    elif process_path is not None or package_names:
        process_fields = []
        if process_user is not None:
            process_fields.append(_field_bytes(3, process_user.encode()))
        if process_path is not None:
            process_fields.append(_field_bytes(4, process_path.encode()))
        process_fields.extend(_field_bytes(5, name.encode()) for name in package_names)
        fields.append(_field_bytes(22, _message(*process_fields)))
    return _message(*fields)


def _event(event_type: int, connection_id: str, connection: bytes | None = None) -> bytes:
    fields = [_field_varint(1, event_type), _field_bytes(2, connection_id.encode())]
    if connection is not None:
        fields.append(_field_bytes(3, connection))
    return _message(*fields)


def _events_message(events: list[bytes], reset: bool = False) -> bytes:
    fields = [_field_bytes(1, event) for event in events]
    if reset:
        fields.append(_field_varint(2, 1))
    return _message(*fields)


# -- gRPC decoding ----------------------------------------------------------


def test_parse_connection_events_reads_every_field() -> None:
    """NEW events carry the whole connection snapshot."""
    update = parse_connection_events(
        _events_message([_event(0, "0c1d2e3f", _connection_message())], reset=True)
    )
    assert update.reset is True
    assert update.closed_ids == []
    assert len(update.connections) == 1

    connection = update.connections[0]
    assert connection.id == "0c1d2e3f"
    assert connection.network == "tcp"
    assert connection.protocol == "https"
    assert connection.source == "192.168.1.5:51234"
    assert connection.destination == "93.184.216.34:443"
    assert connection.host == "example.com"
    assert connection.rule == "geosite-example"
    assert connection.outbound == "proxy"
    assert connection.chain == ["proxy", "hk"]
    assert connection.upload_total == 1000
    assert connection.download_total == 2000
    assert connection.created_at == 1730000000000


def test_parse_connection_events_closed_by_id() -> None:
    """A CLOSED event only needs its id; no snapshot is required."""
    update = parse_connection_events(_events_message([_event(2, "abc")]))
    assert update.closed_ids == ["abc"]
    assert update.connections == []
    assert update.reset is False


def test_parse_connection_events_skips_delta_only_updates() -> None:
    """An UPDATE without a snapshot must not replace the known connection."""
    update = parse_connection_events(
        _events_message(
            [_event(1, "abc"), _event(0, "def", _connection_message(connection_id="def"))]
        )
    )
    assert [item.id for item in update.connections] == ["def"]
    assert update.closed_ids == []


def test_parse_connection_events_process_info() -> None:
    """ProcessInfo renders as "path (user)" like the clash snapshot does."""
    update = parse_connection_events(
        _events_message(
            [
                _event(
                    0,
                    "pid",
                    _connection_message(
                        connection_id="pid",
                        process_path="/usr/bin/curl",
                        process_user="root",
                    ),
                )
            ]
        )
    )
    assert update.connections[0].process == "/usr/bin/curl (root)"


def test_parse_connection_events_process_falls_back_to_package_name() -> None:
    """Android connections report package names instead of a process path."""
    # A real Android ProcessInfo always carries userId = -1 ("unknown"); the
    # proto3 default 0 would mean "root", which is why it is sent explicitly.
    process = _message(_field_varint(2, (1 << 64) - 1), _field_bytes(5, b"com.example"))
    update = parse_connection_events(
        _events_message(
            [_event(0, "pkg", _connection_message(connection_id="pkg", process=process))]
        )
    )
    assert update.connections[0].process == "com.example"


def test_parse_connection_events_process_user_id_appended() -> None:
    """An unresolved user id is appended, matching the clash snapshot format."""
    process = _message(_field_varint(2, (1 << 64) - 2), _field_bytes(4, b"/usr/bin/curl"))
    update = parse_connection_events(
        _events_message(
            [_event(0, "uid", _connection_message(connection_id="uid", process=process))]
        )
    )
    assert update.connections[0].process == "/usr/bin/curl (-2)"


def test_parse_connection_events_tolerates_missing_optional_fields() -> None:
    """A bare message decodes to an empty, not broken, connection."""
    update = parse_connection_events(_events_message([_event(0, "minimal", _message())]))
    connection = update.connections[0]
    assert connection.id == "minimal"
    assert connection.chain == []
    assert connection.protocol == ""
    assert connection.upload_total == 0


# -- clash snapshot ---------------------------------------------------------


CLASH_SNAPSHOT = {
    "downloadTotal": 200000,
    "uploadTotal": 100000,
    "memory": 42,
    "connections": [
        {
            "id": "6f9a1c0e-1111-2222-3333-444455556666",
            "metadata": {
                "network": "tcp",
                "type": "tun/tun-in",
                "sourceIP": "192.168.1.5",
                "sourcePort": "51234",
                "destinationIP": "93.184.216.34",
                "destinationPort": "443",
                "host": "example.com",
                "processPath": "/usr/bin/curl",
            },
            "upload": 1000,
            "download": 2000,
            "start": "2026-11-01T19:20:13.123456789+03:00",
            "chains": ["proxy", "hk"],
            "rule": "geosite-example => route",
        }
    ],
}


def test_parse_clash_snapshot_flattens_the_connection() -> None:
    """The nested clash metadata is unpacked into the shared flat model."""
    connections, memory, upload_total, download_total = parse_connections_snapshot(CLASH_SNAPSHOT)
    assert memory == 42
    assert upload_total == 100000
    assert download_total == 200000
    assert len(connections) == 1

    connection = connections[0]
    assert connection.id == "6f9a1c0e-1111-2222-3333-444455556666"
    assert connection.network == "tcp"
    assert connection.source == "192.168.1.5:51234"
    assert connection.destination == "93.184.216.34:443"
    assert connection.host == "example.com"
    assert connection.process == "/usr/bin/curl"
    assert connection.chain == ["proxy", "hk"]
    # The last chain entry is the outbound that carried the connection.
    assert connection.outbound == "hk"
    assert connection.rule == "geosite-example => route"
    # Totals come from the snapshot counters, not from a per-second delta.
    assert connection.upload_total == 1000
    assert connection.download_total == 2000
    assert connection.upload == 0
    assert connection.download == 0
    # RFC 3339 with nanoseconds, converted to epoch milliseconds.
    assert connection.created_at == 1793550013123


def test_parse_clash_snapshot_survives_a_missing_list() -> None:
    """Older builds answer without the list; that must not raise."""
    assert parse_connections_snapshot({}) == ([], 0, 0, 0)
    assert parse_connections_snapshot({"connections": None}) == ([], 0, 0, 0)


def test_parse_clash_snapshot_rejects_a_non_object() -> None:
    with pytest.raises(ClashApiError):
        parse_connections_snapshot([])


def test_parse_clash_snapshot_accepts_numeric_start() -> None:
    """A few forks send a Unix timestamp instead of an RFC 3339 string."""
    snapshot = {
        "connections": [
            {
                "id": "x",
                "metadata": {},
                "start": 1730000000,
                "chains": [],
                "upload": 0,
                "download": 0,
            }
        ]
    }
    connections, *_ = parse_connections_snapshot(snapshot)
    assert connections[0].created_at == 1730000000000
    assert connections[0].outbound == ""


# -- coordinator ------------------------------------------------------------


def _entry(entry_id: str = "conn") -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA, options={}, entry_id=entry_id)


async def _coordinator(hass: HomeAssistant, client=None) -> SingBoxCoordinator:
    entry = _entry()
    entry.add_to_hass(hass)
    return SingBoxCoordinator(hass, entry, client or AsyncMock(), BACKEND_CLASH, 5)


async def test_connection_events_are_applied_as_a_delta(hass: HomeAssistant) -> None:
    """NEW/UPDATE add, CLOSED removes, reset drops everything first."""
    coordinator = await _coordinator(hass)
    first = SingBoxConnection(id="a", network="tcp")
    second = SingBoxConnection(id="b", network="udp")

    coordinator._apply_connection_events(SingBoxConnectionUpdate(connections=[first, second]))
    assert {item.id for item in coordinator.connections} == {"a", "b"}

    coordinator._apply_connection_events(SingBoxConnectionUpdate(closed_ids=["a"]))
    assert [item.id for item in coordinator.connections] == ["b"]

    # A reset frame is authoritative: it drops what is not in the frame.
    coordinator._apply_connection_events(SingBoxConnectionUpdate(connections=[first], reset=True))
    assert [item.id for item in coordinator.connections] == ["a"]


async def test_connection_stream_does_not_clobber_the_status_counter(
    hass: HomeAssistant,
) -> None:
    """connections_in stays owned by the status frame, not by the event stream."""
    coordinator = await _coordinator(hass)
    coordinator._apply_status({3: [7], 4: [0]})
    assert coordinator.data.connections_in == 7

    coordinator._apply_connection_events(
        SingBoxConnectionUpdate(connections=[SingBoxConnection(id="only-one")])
    )
    assert coordinator.data.connections_in == 7
    assert len(coordinator.connections) == 1


async def test_clash_poll_stores_the_full_connection_list(hass: HomeAssistant) -> None:
    """The clash poll feeds both the counters and the connection list."""
    client = AsyncMock()
    client.get_connections_snapshot = AsyncMock(
        return_value=(
            1,
            42,
            100000,
            200000,
            [SingBoxConnection(id="clash-1", network="tcp")],
        )
    )
    coordinator = await _coordinator(hass, client)
    await coordinator._apply_clash_connections()

    assert coordinator.data.connections_in == 1
    assert coordinator.data.memory == 42
    assert [item.id for item in coordinator.connections] == ["clash-1"]


async def test_connections_stream_is_registered_for_grpc(hass: HomeAssistant) -> None:
    """The gRPC backend keeps the list through SubscribeConnections."""
    client = AsyncMock()
    client.get_version = AsyncMock(return_value=("1.15.0", 2))
    client.get_started_at = AsyncMock(return_value=0)
    client.get_clash_mode_status = AsyncMock(side_effect=GrpcError(5, "no clash api"))
    coordinator = await _coordinator(hass, client)
    coordinator.backend = BACKEND_GRPC
    await coordinator._setup_grpc()

    assert "_run_connections_stream" in [item.__name__ for item in coordinator._stream_factories]


async def test_unsupported_connections_stream_is_retired(hass: HomeAssistant) -> None:
    """UNIMPLEMENTED marks the feature unsupported and ends the stream."""
    coordinator = await _coordinator(hass)

    def _stream():
        raise GrpcError(GRPC_STATUS_UNIMPLEMENTED, "connection tracking not available")

    await coordinator._run_stream("connections", _stream, coordinator._apply_connection_events)
    assert coordinator.connections_supported is False


async def test_transient_stream_error_keeps_connections_supported(hass: HomeAssistant) -> None:
    """A normal reconnect must not be mistaken for "not supported"."""
    coordinator = await _coordinator(hass)

    async def _stream():
        raise ConnectionError("lost")
        yield  # pragma: no cover

    pauses = 0

    async def _pause(delay: float) -> bool:
        nonlocal pauses
        pauses += 1
        return pauses < 2

    coordinator._pause = _pause  # type: ignore[method-assign]
    await coordinator._run_stream("connections", _stream, coordinator._apply_connection_events)
    assert coordinator.connections_supported is True


# -- websocket command ------------------------------------------------------

CONNECTION_PAYLOAD_FIELDS = {
    "id",
    "network",
    "protocol",
    "source",
    "destination",
    "host",
    "rule",
    "outbound",
    "chain",
    "process",
    "upload",
    "download",
    "upload_total",
    "download_total",
    "created_at",
}


async def _ws_payload(hass: HomeAssistant, coordinator: SingBoxCoordinator, client, **msg) -> dict:
    """Send singbox/connections over a real websocket and return the response."""
    from custom_components.singbox import _async_register_websocket_api

    _async_register_websocket_api(hass)
    hass.data[DOMAIN] = {coordinator.config_entry.entry_id: coordinator}
    await client.send_json({"id": 5, "type": "singbox/connections", **msg})
    return await client.receive_json()


async def test_ws_command_returns_flat_connections(hass: HomeAssistant, hass_ws_client) -> None:
    """singbox/connections answers with the documented flat payload."""
    entry = _entry("ws")
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, AsyncMock(), BACKEND_CLASH, 5)
    coordinator._set_connections(
        [
            SingBoxConnection(
                id="ws-1",
                network="tcp",
                protocol="https",
                source="1.2.3.4:1",
                destination="5.6.7.8:443",
                host="example.com",
                rule="rule",
                outbound="proxy",
                chain=["proxy", "hk"],
                process="curl",
                upload=1,
                download=2,
                upload_total=3,
                download_total=4,
                created_at=1730000000000,
            )
        ]
    )

    client = await hass_ws_client(hass)
    response = await _ws_payload(hass, coordinator, client)
    if not response.get("success"):
        pytest.fail(f"websocket command failed: {response}")

    payload = response["result"]
    assert payload["count"] == 1
    assert payload["supported"] is True

    connection_payload = payload["connections"][0]
    assert set(connection_payload) == CONNECTION_PAYLOAD_FIELDS
    assert connection_payload == {
        "id": "ws-1",
        "network": "tcp",
        "protocol": "https",
        "source": "1.2.3.4:1",
        "destination": "5.6.7.8:443",
        "host": "example.com",
        "rule": "rule",
        "outbound": "proxy",
        "chain": ["proxy", "hk"],
        "process": "curl",
        "upload": 1,
        "download": 2,
        "upload_total": 3,
        "download_total": 4,
        "created_at": 1730000000000,
    }
    # The payload must be JSON-serialisable as-is.
    json.dumps(payload)


async def test_ws_command_reports_unsupported_backend(hass: HomeAssistant, hass_ws_client) -> None:
    """supported=False is a separate signal from an empty list."""
    entry = _entry("unsup")
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, AsyncMock(), BACKEND_GRPC, 5)
    coordinator._connections_supported = False

    client = await hass_ws_client(hass)
    response = await _ws_payload(hass, coordinator, client, entry_id=entry.entry_id)
    assert response["result"] == {"connections": [], "count": 0, "supported": False}


async def test_ws_command_accepts_an_explicit_entry_id(hass: HomeAssistant, hass_ws_client) -> None:
    """entry_id selects a specific config entry when several are loaded."""
    entry = _entry("explicit")
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, AsyncMock(), BACKEND_CLASH, 5)
    coordinator._set_connections([SingBoxConnection(id="explicit-1")])

    client = await hass_ws_client(hass)
    response = await _ws_payload(hass, coordinator, client, entry_id=entry.entry_id)
    assert response["result"]["connections"][0]["id"] == "explicit-1"


async def test_ws_command_reports_unknown_entry(hass: HomeAssistant, hass_ws_client) -> None:
    """An unknown entry_id answers with a not-found error, not a traceback."""
    from homeassistant.components import websocket_api

    entry = _entry("known")
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, AsyncMock(), BACKEND_CLASH, 5)

    client = await hass_ws_client(hass)
    response = await _ws_payload(hass, coordinator, client, entry_id="nope")
    assert response["success"] is False
    assert response["error"]["code"] == websocket_api.ERR_NOT_FOUND


async def test_websocket_api_registration_is_idempotent(hass: HomeAssistant) -> None:
    """Registering twice must not duplicate the handler."""
    from homeassistant.components import websocket_api

    from custom_components.singbox import DATA_WS_REGISTERED, _async_register_websocket_api

    _async_register_websocket_api(hass)
    first = dict(hass.data[websocket_api.DOMAIN])
    _async_register_websocket_api(hass)

    assert hass.data[DATA_WS_REGISTERED] is True
    assert set(hass.data[websocket_api.DOMAIN]) == set(first)
    assert "singbox/connections" in first
