"""Tests for per-outbound traffic: the sampler and its coordinator wiring."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.singbox.backend import BACKEND_CLASH, BACKEND_GRPC
from custom_components.singbox.const import DOMAIN
from custom_components.singbox.coordinator import (
    _TRAFFIC_STALE_AFTER,
    _TRAFFIC_TAG_GRACE,
    OutboundTrafficSampler,
    SingBoxCoordinator,
)
from custom_components.singbox.grpc import SingBoxConnection

from .conftest import MOCK_ENTRY_DATA


def _connection(
    connection_id: str,
    chain: tuple[str, ...],
    upload: int = 0,
    download: int = 0,
) -> SingBoxConnection:
    """A connection as the clash snapshot parses it (cumulative counters)."""
    return SingBoxConnection(
        id=connection_id,
        chain=list(chain),
        outbound=chain[-1] if chain else "",
        upload_total=upload,
        download_total=download,
    )


def _entry(entry_id: str = "traffic") -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA, options={}, entry_id=entry_id)


async def _coordinator(hass: HomeAssistant, backend: str = BACKEND_CLASH) -> SingBoxCoordinator:
    entry = _entry()
    entry.add_to_hass(hass)
    return SingBoxCoordinator(hass, entry, AsyncMock(), backend, 5)


# -- sampler ----------------------------------------------------------------


def test_first_snapshot_only_establishes_the_baseline() -> None:
    """A rate needs two points in time; one snapshot can only be the baseline."""
    sampler = OutboundTrafficSampler()
    assert sampler.sample([_connection("a", ("node",), 100, 200)], (100, 200), 0.0) is None
    assert sampler.rates == {}
    assert sampler.windows == 0


def test_increment_is_divided_by_the_measured_elapsed_time() -> None:
    """The window is the real elapsed time, not the nominal poll interval."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("node",), 0, 0)], (0, 0), 0.0)
    # 4000 bytes over 4 s despite a nominal 10 s interval.
    sample = sampler.sample([_connection("a", ("node",), 2000, 2000)], (2000, 2000), 4.0)

    assert sample is not None
    assert sampler.rates["node"] == (500, 500)
    assert sample.window_seconds == pytest.approx(4.0)


def test_increment_is_attributed_to_every_tag_of_the_chain() -> None:
    """The card needs the speed of the node, of its group and of the leaf."""
    sampler = OutboundTrafficSampler()
    chain = ("eu vless: EU-openwrt", "telaga-urltest-out", "telaga-out")
    sampler.sample([_connection("a", chain, 0, 0)], (0, 0), 0.0)
    sampler.sample([_connection("a", chain, 1000, 3000)], (1000, 3000), 2.0)

    for tag in chain:
        assert sampler.rates[tag] == (500, 1500)


def test_a_new_connection_contributes_nothing_in_its_first_window() -> None:
    """Its counters already carry the burst since it opened; do not fake a spike."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("node",), 0, 0)], (0, 0), 0.0)
    # A connection that appeared with 1 MB already on its counters.
    sampler.sample(
        [
            _connection("a", ("node",), 0, 0),
            _connection("b", ("node",), 1_000_000, 0),
        ],
        (1_000_000, 0),
        1.0,
    )
    # The tag is reported (it has a live connection) but with no bytes: the
    # 1 MB it arrived with could have been moved at any point since it opened.
    assert sampler.rates == {"node": (0, 0)}
    assert sampler.total == (0, 0)


def test_a_counter_reset_is_not_negative_traffic() -> None:
    """Reused ids and restarted connections must clamp to zero, not go negative."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("node",), 5000, 5000)], (5000, 5000), 0.0)
    sampler.sample([_connection("a", ("node",), 10, 20)], (10, 20), 1.0)
    assert sampler.rates == {"node": (0, 0)}
    assert sampler.total == (0, 0)


def test_a_tag_repeated_in_one_chain_is_attributed_once() -> None:
    """A pathological chain must not count the same bytes twice."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("dup", "dup"), 0, 0)], (0, 0), 0.0)
    sampler.sample([_connection("a", ("dup", "dup"), 100, 0)], (100, 0), 1.0)
    assert sampler.rates["dup"] == (100, 0)


def test_per_tag_numbers_overlap_but_total_stays_honest() -> None:
    """Summing the tags exceeds the real traffic; total keeps the real figure."""
    sampler = OutboundTrafficSampler()
    chain = ("group", "leaf")
    sampler.sample([_connection("a", chain, 0, 0)], (0, 0), 0.0)
    sampler.sample([_connection("a", chain, 1000, 1000)], (1000, 1000), 1.0)

    per_tag_up = sum(up for up, _ in sampler.rates.values())
    assert per_tag_up == 2000  # counted for "group" and for "leaf"
    assert sampler.total == (1000, 1000)


def test_a_window_shorter_than_the_minimum_is_not_a_measurement() -> None:
    """Two snapshots back to back must not divide by a few milliseconds."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("node",), 0, 0)], (0, 0), 0.0)
    assert sampler.sample([_connection("a", ("node",), 10, 0)], (10, 0), 0.01) is None
    # The baseline is kept, so the bytes land in the next full window.
    sample = sampler.sample([_connection("a", ("node",), 100, 0)], (100, 0), 1.0)
    assert sample is not None
    assert sampler.rates["node"] == (100, 0)


def test_a_vanished_tag_lingers_for_the_grace_period_then_goes() -> None:
    """Dropping it at once makes an "active now" filter flicker."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("gone",), 0, 0)], (0, 0), 0.0)
    sampler.sample([_connection("a", ("gone",), 100, 0)], (100, 0), 1.0)
    assert sampler.rates["gone"] == (100, 0)

    # The connection is closed: the tag keeps a zero rate for a while.
    now = 1.0
    for _ in range(_TRAFFIC_TAG_GRACE):
        now += 1.0
        sampler.sample([], (100, 0), now)
        assert sampler.rates.get("gone") == (0, 0)
    sampler.sample([], (100, 0), now + 1.0)
    assert "gone" not in sampler.rates


def test_an_idle_tag_with_an_open_connection_is_kept_at_zero() -> None:
    """Idle is not gone: the outbound still exists, it just moved no bytes."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("idle",), 0, 0)], (0, 0), 0.0)
    sampler.sample([_connection("a", ("idle",), 100, 0)], (100, 0), 1.0)
    for window in range(2, 6):
        sampler.sample([_connection("a", ("idle",), 100, 0)], (100, 0), float(window))
        assert sampler.rates["idle"] == (0, 0)


def test_sampled_at_is_an_iso_timestamp() -> None:
    """The card renders "now"; it must be a parseable ISO-8601 moment."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("node",), 0, 0)], (0, 0), 0.0)
    sample = sampler.sample([_connection("a", ("node",), 1, 1)], (1, 1), 1.0)
    assert sample is not None
    assert sample.sampled_at.endswith(("+00:00", "+03:00", "+02:00", "+01:00", "Z")) or (
        sample.sampled_at[4] == "-"
    )
    from datetime import datetime

    datetime.fromisoformat(sample.sampled_at)


def test_reset_forgets_the_baseline() -> None:
    """After a backend restart the old counters are meaningless."""
    sampler = OutboundTrafficSampler()
    sampler.sample([_connection("a", ("node",), 0, 0)], (0, 0), 0.0)
    sampler.sample([_connection("a", ("node",), 100, 100)], (100, 100), 1.0)
    sampler.reset()

    assert sampler.sample([_connection("a", ("node",), 900, 900)], (900, 900), 2.0) is None
    assert sampler.rates == {}


# -- coordinator wiring -----------------------------------------------------


async def test_clash_poll_publishes_the_traffic_payload(hass: HomeAssistant) -> None:
    """The connections poll costs no extra request and yields the rates."""
    coordinator = await _coordinator(hass)
    client = coordinator.client
    client.get_connections_snapshot = AsyncMock(
        return_value=(
            1,
            42,
            0,
            0,
            [_connection("a", ("group", "leaf"), 0, 0)],
        )
    )
    await coordinator._apply_clash_connections()
    # First poll is the baseline: no rate yet, so the feature is not "available".
    assert coordinator.outbound_traffic_available is False
    assert coordinator.outbound_tags() == ["group", "leaf"]

    # Rewind the window instead of sleeping: 2 s and 5 KB later.
    coordinator._traffic_sampler._window_start -= 2.0
    client.get_connections_snapshot = AsyncMock(
        return_value=(
            1,
            42,
            5000,
            5000,
            [_connection("a", ("group", "leaf"), 2500, 2500)],
        )
    )
    await coordinator._apply_clash_connections()

    assert coordinator.outbound_traffic_available is True
    assert coordinator.outbound_traffic == {"group": (1250, 1250), "leaf": (1250, 1250)}
    # 2500 bytes over 2 s: the total is the real figure, while the per-tag
    # numbers overlap and add up to twice as much for this two-tag chain.
    assert coordinator.outbound_traffic_total == (1250, 1250)
    assert sum(up for up, _ in coordinator.outbound_traffic.values()) == 2500
    assert coordinator.outbound_traffic_sampled_at
    assert coordinator.data.traffic["available"] is True
    assert coordinator.data.traffic["outbounds"]["leaf"] == {"up": 1250, "down": 1250}


async def test_outbound_traffic_is_a_copy(hass: HomeAssistant) -> None:
    """A caller must not be able to mutate the coordinator's state."""
    coordinator = await _coordinator(hass)
    client = coordinator.client
    for upload in (0, 100):
        client.get_connections_snapshot = AsyncMock(
            return_value=(1, 0, upload, 0, [_connection("a", ("node",), upload, 0)])
        )
        if upload:
            coordinator._traffic_sampler._window_start -= 1.0
        await coordinator._apply_clash_connections()

    snapshot = coordinator.outbound_traffic
    snapshot["node"] = (999, 999)
    snapshot["injected"] = (1, 1)
    assert "injected" not in coordinator.outbound_traffic


async def test_grpc_backend_reports_traffic_as_unavailable(hass: HomeAssistant) -> None:
    """No per-connection counters to diff: say so instead of pretending zero."""
    coordinator = await _coordinator(hass, BACKEND_GRPC)

    assert coordinator.outbound_traffic_available is False
    assert coordinator.outbound_traffic == {}
    assert coordinator.outbound_traffic_sampled_at == ""
    assert coordinator.outbound_tags() == []
    assert coordinator.has_outbound_traffic("anything") is False
    assert coordinator.traffic_payload() == {
        "available": False,
        "now": "",
        "outbounds": {},
        "total": {"up": 0, "down": 0},
    }


async def test_an_unsupported_connection_list_disables_traffic(hass: HomeAssistant) -> None:
    """A build without connection tracking has no traffic to attribute."""
    coordinator = await _coordinator(hass)
    coordinator._connections_supported = False
    coordinator._traffic_sample_monotonic = time.monotonic()
    assert coordinator.outbound_traffic_available is False


async def test_a_stale_sample_is_not_reported_as_live(hass: HomeAssistant) -> None:
    """A wedged poll must not keep serving yesterday's rates as current."""
    coordinator = await _coordinator(hass)
    coordinator._traffic_sample_monotonic = time.monotonic() - (_TRAFFIC_STALE_AFTER + 1)
    assert coordinator.outbound_traffic_available is False


async def test_traffic_listener_is_notified_and_new_tags_trigger_discovery(
    hass: HomeAssistant,
) -> None:
    """The sensor platform creates entities from the listener, not from a poll."""
    coordinator = await _coordinator(hass)
    calls: list[int] = []

    def _listener() -> None:
        calls.append(1)

    coordinator.async_add_traffic_listener(_listener)

    client = coordinator.client
    client.get_connections_snapshot = AsyncMock(
        return_value=(1, 0, 0, 0, [_connection("a", ("node",), 0, 0)])
    )
    await coordinator._apply_clash_connections()
    assert calls == []  # the baseline is not a sample yet

    coordinator._traffic_sampler._window_start -= 1.0
    client.get_connections_snapshot = AsyncMock(
        return_value=(1, 0, 50, 50, [_connection("a", ("node",), 50, 50)])
    )
    await coordinator._apply_clash_connections()
    assert calls == [1]

    coordinator.async_remove_traffic_listener(_listener)
    coordinator._traffic_sampler._window_start -= 1.0
    client.get_connections_snapshot = AsyncMock(
        return_value=(1, 0, 80, 80, [_connection("a", ("node",), 80, 80)])
    )
    await coordinator._apply_clash_connections()
    assert calls == [1]


async def test_has_outbound_traffic_follows_the_live_connection_list(
    hass: HomeAssistant,
) -> None:
    """ "Exists now" is the snapshot, not the sampler's grace period."""
    coordinator = await _coordinator(hass)
    client = coordinator.client
    for upload in (0, 100):
        client.get_connections_snapshot = AsyncMock(
            return_value=(1, 0, upload, 0, [_connection("a", ("old",), upload, 0)])
        )
        if upload:
            coordinator._traffic_sampler._window_start -= 1.0
        await coordinator._apply_clash_connections()
    assert coordinator.has_outbound_traffic("old") is True
    assert coordinator.outbound_traffic["old"] == (100, 0)

    coordinator._traffic_sampler._window_start -= 1.0
    client.get_connections_snapshot = AsyncMock(
        return_value=(1, 0, 0, 0, [_connection("b", ("new",), 0, 0)])
    )
    await coordinator._apply_clash_connections()

    assert coordinator.has_outbound_traffic("new") is True
    assert coordinator.has_outbound_traffic("old") is False
    # The sampler still holds "old" for a couple of windows so the card does
    # not flicker, which is exactly why the two answers are kept apart.
    assert "old" in coordinator.outbound_traffic


# -- websocket API ----------------------------------------------------------


async def _ws_status(hass: HomeAssistant, coordinator: SingBoxCoordinator, client) -> dict:
    from custom_components.singbox import _async_register_websocket_api

    _async_register_websocket_api(hass)
    hass.data[DOMAIN] = {coordinator.config_entry.entry_id: coordinator}
    await client.send_json({"id": 7, "type": "singbox/status"})
    return await client.receive_json()


async def test_status_command_returns_the_traffic_block(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """The card reads traffic from singbox/status, not from sensor states."""
    coordinator = await _coordinator(hass)
    client = coordinator.client
    for upload in (0, 400):
        client.get_connections_snapshot = AsyncMock(
            return_value=(
                1,
                0,
                upload,
                upload,
                [_connection("a", ("group", "leaf"), upload, upload)],
            )
        )
        if upload:
            coordinator._traffic_sampler._window_start -= 2.0
        await coordinator._apply_clash_connections()

    ws = await hass_ws_client(hass)
    response = await _ws_status(hass, coordinator, ws)
    if not response.get("success"):
        pytest.fail(f"websocket command failed: {response}")

    traffic = response["result"]["traffic"]
    # 400 bytes over 2 s = 200 B/s, attributed to both tags of the chain
    # (that overlap is deliberate); the total is the real figure.
    assert traffic == {
        "available": True,
        "now": coordinator.outbound_traffic_sampled_at,
        "outbounds": {"group": {"up": 200, "down": 200}, "leaf": {"up": 200, "down": 200}},
        "total": {"up": 200, "down": 200},
    }
    # The payload must be JSON-serialisable as-is.
    json.dumps(response["result"])


# -- entities ---------------------------------------------------------------


async def test_traffic_entities_are_named_by_direction_not_by_tag(
    hass: HomeAssistant,
) -> None:
    """Names must not collide with the ping sensor of the same outbound.

    A bare tag as the name gave "telaga-out" twice: the ping sensor and both
    traffic sensors would fight for the same name, Home Assistant would move
    the later ones to "_2"/"_3", and the entity read as a delay rather than a
    rate. The tag now fills a placeholder inside a translated name.
    """
    from custom_components.singbox.sensor import SingBoxOutboundTrafficSensor

    coordinator = await _coordinator(hass)
    up = SingBoxOutboundTrafficSensor(coordinator, "telaga-out", "up")
    down = SingBoxOutboundTrafficSensor(coordinator, "telaga-out", "down")

    assert not hasattr(up, "_attr_name")
    assert up.translation_placeholders == {"outbound": "telaga-out"}
    assert up.translation_key == "outbound_up"
    assert down.translation_key == "outbound_down"
    # Distance from the ping sensor: different unique ids and different
    # suggested object ids, so the registry keeps all three entities.
    assert up.unique_id == f"{coordinator.config_entry.entry_id}_out_up_telaga-out"
    assert down.unique_id == f"{coordinator.config_entry.entry_id}_out_down_telaga-out"


@pytest.mark.parametrize("language", ["strings", "en", "ru"])
def test_traffic_entity_names_consume_the_placeholder(language: str) -> None:
    """Every translated name has to accept the {outbound} placeholder.

    A name without it would format fine but drop the tag, which silently
    turns every per-outbound sensor into one indistinguishable "Outbound
    uplink"; a name with a *different* placeholder raises KeyError at name
    resolution time and Home Assistant reports a broken entity.
    """
    from custom_components.singbox import __file__ as package_file

    path = Path(package_file).parent
    if language != "strings":
        path = path / "translations" / f"{language}.json"
    else:
        path = path / "strings.json"
    names = json.loads(path.read_text(encoding="utf-8"))["entity"]["sensor"]

    for key in ("outbound_uplink", "outbound_downlink"):
        name = names[key]["name"]
        assert "{outbound}" in name
        assert "eu vless: EU2" in name.format(outbound="eu vless: EU2")


async def test_setup_creates_two_sensors_per_outbound(hass: HomeAssistant) -> None:
    """One up and one down sensor per tag, created when the first rate lands."""
    from custom_components.singbox import sensor as sensor_platform

    coordinator = await _coordinator(hass)
    client = coordinator.client
    for upload in (0, 200):
        client.get_connections_snapshot = AsyncMock(
            return_value=(
                1,
                0,
                upload,
                upload,
                [_connection("a", ("group", "leaf"), upload, upload)],
            )
        )
        if upload:
            coordinator._traffic_sampler._window_start -= 2.0
        await coordinator._apply_clash_connections()
    assert coordinator.outbound_traffic_available is True

    hass.data.setdefault(DOMAIN, {})[coordinator.config_entry.entry_id] = coordinator
    added: list = []
    await sensor_platform.async_setup_entry(
        hass,
        coordinator.config_entry,
        lambda entities, update_before_add=False: added.extend(entities),
    )
    traffic = [
        entity for entity in added if type(entity).__name__ == "SingBoxOutboundTrafficSensor"
    ]

    assert {
        (entity.translation_key, entity.translation_placeholders["outbound"]) for entity in traffic
    } == {
        ("outbound_up", "group"),
        ("outbound_down", "group"),
        ("outbound_up", "leaf"),
        ("outbound_down", "leaf"),
    }
    # 100 B/s per connection over 2 s, attributed to both tags of the chain.
    up = next(e for e in traffic if e.translation_key == "outbound_up")
    assert up.native_value == 100


async def test_status_command_reports_unavailable_traffic_on_grpc(
    hass: HomeAssistant, hass_ws_client
) -> None:
    """An unsupported backend is a flag, not an error and not a zero rate."""
    coordinator = await _coordinator(hass, BACKEND_GRPC)
    ws = await hass_ws_client(hass)
    response = await _ws_status(hass, coordinator, ws)
    if not response.get("success"):
        pytest.fail(f"websocket command failed: {response}")

    assert response["result"]["traffic"]["available"] is False
    assert response["result"]["traffic"]["outbounds"] == {}
