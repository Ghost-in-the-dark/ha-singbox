"""Tests for the sing-box coordinator: streams, supervision and services."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.singbox.backend import BACKEND_CLASH, BACKEND_GRPC
from custom_components.singbox.clash import ClashApiError
from custom_components.singbox.const import DOMAIN
from custom_components.singbox.coordinator import SingBoxCoordinator
from custom_components.singbox.errors import SingBoxNotSupported
from custom_components.singbox.grpc import (
    GRPC_STATUS_UNAUTHENTICATED,
    GrpcError,
    SingBoxGroup,
    SingBoxGroupItem,
)

from .conftest import MOCK_ENTRY_DATA


class FakeGrpcClient:
    """Minimal stand-in for SingBoxClient."""

    def __init__(self) -> None:
        self.closed = False
        self.status_frames: list[dict] = []
        self.groups: list[SingBoxGroup] = []

    async def close(self) -> None:
        self.closed = True

    async def get_version(self) -> tuple[str, int]:
        return "1.14.0", 1

    async def get_started_at(self) -> int:
        return 0

    async def get_clash_mode_status(self) -> tuple[list[str], str]:
        raise GrpcError(5, "no clash api")

    async def subscribe_status(self, interval_ns: int):
        for frame in self.status_frames:
            yield frame

    async def subscribe_groups(self):
        yield self.groups


def _entry(entry_id: str = "test") -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA, options={}, entry_id=entry_id)


async def _coordinator(hass: HomeAssistant, client=None) -> SingBoxCoordinator:
    entry = _entry()
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, client or FakeGrpcClient(), BACKEND_GRPC, 5)
    return coordinator


# -- traffic rate -----------------------------------------------------------


async def test_traffic_rate_is_averaged_over_the_push_window(
    hass: HomeAssistant,
) -> None:
    """Deltas are summed between pushes and divided by the real interval."""
    coordinator = await _coordinator(hass)
    coordinator._apply_status({6: [100], 7: [400]})
    coordinator._apply_status({6: [100], 7: [400]})
    coordinator._flush_traffic_rate(coordinator._rate_window_start + 2.0)
    assert coordinator.data.uplink == 100.0  # 200 bytes / 2 s
    assert coordinator.data.downlink == 400.0

    # The window restarts empty after a flush.
    coordinator._flush_traffic_rate(coordinator._rate_window_start + 1.0)
    assert coordinator.data.uplink == 0


async def test_rate_window_never_divides_by_zero(hass: HomeAssistant) -> None:
    """Two frames delivered back to back must not explode the rate."""
    coordinator = await _coordinator(hass)
    coordinator._apply_status({6: [10], 7: [10]})
    coordinator._flush_traffic_rate(coordinator._rate_window_start)
    assert coordinator.data.uplink == pytest.approx(20.0)  # 10 B / 0.5 s


# -- availability / pushing -------------------------------------------------


async def test_pushes_are_throttled_but_recovery_is_immediate(
    hass: HomeAssistant,
) -> None:
    """Recovery flips availability at once; steady frames are throttled."""
    coordinator = await _coordinator(hass)
    calls = 0

    def _listener() -> None:
        nonlocal calls
        calls += 1

    coordinator.async_add_listener(_listener)
    coordinator._mark_available()
    assert calls == 1  # recovering from "not yet successful"

    coordinator._mark_available()
    coordinator._mark_available()
    assert calls == 1  # inside the 5 s push window

    coordinator._mark_unavailable(None)
    assert calls == 2
    coordinator._mark_available()
    assert calls == 3  # recovery pushes immediately instead of waiting


async def test_discovery_listeners_are_notified(hass: HomeAssistant) -> None:
    """New groups/proxies trigger the entity discovery callback."""
    coordinator = await _coordinator(hass)
    hits: list[int] = []
    coordinator.async_add_discovery_listener(lambda: hits.append(1))
    coordinator._mark_available()  # recovery + discovery
    assert hits == [1]
    coordinator.async_remove_discovery_listener(coordinator._discovery_listeners[0])
    coordinator._mark_unavailable(None)
    coordinator._mark_available()
    assert len(coordinator._discovery_listeners) == 0


# -- stream supervision -----------------------------------------------------


async def test_dead_stream_task_is_restarted(hass: HomeAssistant) -> None:
    """A stream task that dies must be restarted, not left silently gone."""
    coordinator = await _coordinator(hass)
    restarted = asyncio.Event()

    async def _stream() -> None:
        restarted.set()
        await asyncio.sleep(3600)

    coordinator._stream_factories = [_stream]
    coordinator._start_streams()
    first = coordinator.stream_tasks[0]

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first

    coordinator._supervise_stream_tasks()
    second = coordinator.stream_tasks[0]
    assert second is not first
    await asyncio.wait_for(restarted.wait(), timeout=1)
    await coordinator.async_shutdown()


async def test_stream_survives_unexpected_errors(hass: HomeAssistant) -> None:
    """A decoding error must not kill the stream loop (it used to silently)."""
    coordinator = await _coordinator(hass)
    attempts = 0

    async def _stream():
        nonlocal attempts
        attempts += 1
        raise ValueError("truncated frame")
        yield  # pragma: no cover

    pauses = 0

    async def _pause(delay: float) -> bool:
        nonlocal pauses
        pauses += 1
        return pauses < 2

    coordinator._pause = _pause  # type: ignore[method-assign]
    await coordinator._run_stream("test", _stream, lambda frame: None)
    assert attempts == 2


async def test_stream_auth_failure_starts_reauth(hass: HomeAssistant) -> None:
    """A rejected secret starts a reauth flow instead of spinning forever."""
    coordinator = await _coordinator(hass)

    async def _stream():
        raise GrpcError(GRPC_STATUS_UNAUTHENTICATED, "denied")
        yield  # pragma: no cover

    with patch.object(type(coordinator.config_entry), "async_start_reauth") as start_reauth:
        await coordinator._run_stream("test", _stream, lambda frame: None)
    start_reauth.assert_called_once()
    assert coordinator.last_update_success is False


# -- setup / unload ---------------------------------------------------------


async def test_setup_creates_entities_and_unload_removes_services(
    hass: HomeAssistant,
) -> None:
    """Setup forwards the platforms; unloading the last entry drops services."""
    entry = _entry("svc")
    entry.add_to_hass(hass)
    client = FakeGrpcClient()
    client.groups = [
        SingBoxGroup(
            tag="proxy",
            type="Selector",
            selectable=True,
            selected="a",
            is_expand=False,
            items=[SingBoxGroupItem("a", "", 0, 50), SingBoxGroupItem("b", "", 0, 70)],
        )
    ]

    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(return_value=(client, BACKEND_GRPC)),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert hass.states.get("select.sing_box_proxy") is not None
    assert hass.states.get("sensor.sing_box_uplink") is not None

    # Ping sensors must stay enabled: the companion Sing-box Panel Card reads
    # their state for the per-node ping chips, and a disabled registry entry
    # has no state at all (every chip would render as a dash).
    registry = er.async_get(hass)
    ping = registry.async_get("sensor.sing_box_a")
    assert ping is not None
    assert ping.disabled_by is None
    assert hass.states.get("sensor.sing_box_a") is not None
    assert hass.services.has_service(DOMAIN, "select_outbound")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, "select_outbound")


# -- services ---------------------------------------------------------------


async def test_services_report_errors(hass: HomeAssistant) -> None:
    """Backend errors surface as HomeAssistantError, not a traceback."""
    entry = _entry("svc2")
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, FakeGrpcClient(), BACKEND_GRPC, 5)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}
    # register services through the setup helper
    from custom_components.singbox import _async_setup_services

    await _async_setup_services(hass, entry)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "select_outbound",
            {"entry_id": "nope", "group_tag": "g", "outbound_tag": "a"},
            blocking=True,
        )

    coordinator.client.select_outbound = AsyncMock(side_effect=GrpcError(13, "internal"))
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "select_outbound",
            {"entry_id": entry.entry_id, "group_tag": "g", "outbound_tag": "a"},
            blocking=True,
        )

    coordinator.client.set_clash_mode = AsyncMock(side_effect=ClashApiError(0, "nope"))
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "set_clash_mode",
            {"entry_id": entry.entry_id, "mode": "rule"},
            blocking=True,
        )


async def test_set_group_expand_unsupported_on_clash(hass: HomeAssistant) -> None:
    """set_group_expand reports "not supported" instead of HTTP 0."""
    entry = _entry("clash")
    entry.add_to_hass(hass)
    coordinator = SingBoxCoordinator(hass, entry, AsyncMock(), BACKEND_CLASH, 5)
    with pytest.raises(SingBoxNotSupported):
        await coordinator.set_group_expand("g", True)


# -- bundled panel card ------------------------------------------------------


async def test_bundled_card_is_served_and_loaded(hass: HomeAssistant) -> None:
    """The bundle ships with the integration and is exposed as a resource."""
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.setup import async_setup_component

    from custom_components.singbox.frontend import (
        CARD_URL_PATH,
        DATA_CARD_REGISTERED,
        card_path,
        card_url,
    )

    assert card_path().is_file(), "the panel card bundle must ship with the integration"

    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    entry = _entry("card")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(return_value=(FakeGrpcClient(), BACKEND_GRPC)),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # The file is served from an integration static route ...
    assert hass.data[DATA_CARD_REGISTERED] is True
    # ... and advertised through Lovelace, which is what the apps need.
    urls = [item["url"] for item in hass.data[LOVELACE_DATA].resources.async_items()]
    assert card_url() in urls
    # The URL carries a version so an upgraded bundle is not served from the
    # browser's module cache.
    assert urls[0].startswith(CARD_URL_PATH + "?v=")


async def test_card_falls_back_to_extra_module_without_lovelace(
    hass: HomeAssistant,
) -> None:
    """Without a place to store a resource, the card loads as an extra module.

    YAML-mode dashboards (and instances where lovelace is not set up yet)
    cannot take a resource, so registration degrades instead of failing.
    """
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.setup import async_setup_component

    from custom_components.singbox.frontend import card_url

    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    entry = _entry("card5")
    entry.add_to_hass(hass)
    # Simulate a read-only (YAML mode) resource collection: the card then has
    # nowhere to store a resource and must degrade to the extra module.
    hass.data[LOVELACE_DATA].resources = SimpleNamespace(async_items=lambda: [])
    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(return_value=(FakeGrpcClient(), BACKEND_GRPC)),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert card_url() in hass.data[DATA_EXTRA_MODULE_URL].urls


async def test_card_is_available_when_no_entry_loads(hass: HomeAssistant) -> None:
    """The card must exist even while no sing-box entry can be set up.

    This is the "Custom element doesn't exist: singbox-panel-card" case:
    the integration is installed, but an unreachable host or a wrong secret
    keeps the entry out of LOADED. Registration therefore happens in
    async_setup, not async_setup_entry.
    """
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.setup import async_setup_component

    from custom_components.singbox.frontend import card_url

    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    entry = _entry("card3")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(side_effect=ConnectionError("unreachable")),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    # The entry is not loaded, but the card is still advertised to the UI.
    assert entry.state is ConfigEntryState.SETUP_RETRY
    urls = [item["url"] for item in hass.data[LOVELACE_DATA].resources.async_items()]
    assert card_url() in urls


# -- setup error mapping -----------------------------------------------------


@pytest.mark.parametrize(
    ("error", "expected_state"),
    [
        (GrpcError(GRPC_STATUS_UNAUTHENTICATED, "bad secret"), ConfigEntryState.SETUP_ERROR),
        (GrpcError(13, "boom"), ConfigEntryState.SETUP_RETRY),
        (ClashApiError(401, "Unauthorized"), ConfigEntryState.SETUP_ERROR),
        (ConnectionError("refused"), ConfigEntryState.SETUP_RETRY),
        (TimeoutError("slow"), ConfigEntryState.SETUP_RETRY),
    ],
)
async def test_setup_maps_errors(
    hass: HomeAssistant, error: Exception, expected_state: ConfigEntryState
) -> None:
    """A bad secret fails the entry (reauth), an unreachable host just retries."""
    entry = _entry(f"err_{type(error).__name__}")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(side_effect=error),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is expected_state


async def test_stale_card_resource_is_migrated(hass: HomeAssistant) -> None:
    """An unversioned resource from an older release is updated, not duplicated.

    Every release before the versioned URL registered the bare path, and the
    browser then cached that module forever: an upgraded bundle stayed
    invisible until the user cleared storage. The stale entry is rewritten in
    place so exactly one resource loads the card.
    """
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.setup import async_setup_component

    from custom_components.singbox.frontend import CARD_URL_PATH, card_url

    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_create_item({"res_type": "module", "url": CARD_URL_PATH})

    entry = _entry("card9")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(return_value=(FakeGrpcClient(), BACKEND_GRPC)),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    urls = [item["url"] for item in resources.async_items()]
    assert urls == [card_url()], f"expected exactly the versioned URL, got {urls}"


async def test_card_registration_is_idempotent(hass: HomeAssistant) -> None:
    """A reload must not register the static route or the resource twice.

    Registering the same static path twice raises in Home Assistant, and a
    duplicated resource would load the card twice, so both are idempotent.
    """
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    from homeassistant.setup import async_setup_component

    from custom_components.singbox.frontend import card_url

    assert await async_setup_component(hass, "lovelace", {})
    await hass.async_block_till_done()

    entry = _entry("card2")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.singbox.detect_backend",
        new=AsyncMock(return_value=(FakeGrpcClient(), BACKEND_GRPC)),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        resources = hass.data[LOVELACE_DATA].resources
        registered = [item for item in resources.async_items() if item["url"] == card_url()]
        assert len(registered) == 1
        assert registered[0]["type"] == "module"

        # A reload unloads and sets up again without touching the route or
        # duplicating the resource.
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert [item for item in resources.async_items() if item["url"] == card_url()] == registered


# -- blocking I/O ------------------------------------------------------------


async def test_card_version_is_read_off_the_event_loop(hass: HomeAssistant) -> None:
    """The manifest must be read in the executor, never on the loop.

    async_setup runs on the event loop, so a plain Path.read_text() there is a
    blocking call: Home Assistant logs "Detected blocking call to open ...
    inside the event loop" and stalls other integrations during setup. The
    version is resolved through async_add_executor_job and cached per process.
    """
    from custom_components.singbox import frontend

    frontend._VERSION_CACHE = None
    calls: list[str] = []
    real_executor = hass.async_add_executor_job

    async def spy_executor(func, *args):
        calls.append(getattr(func, "__name__", repr(func)))
        return await real_executor(func, *args)

    with patch.object(hass, "async_add_executor_job", side_effect=spy_executor):
        url = await frontend.async_card_url(hass)

    assert url.startswith(frontend.CARD_URL_PATH + "?v=")
    assert "_read_card_version" in calls, f"expected an executor job, got {calls}"

    # Cached: a second call does no filesystem work at all.
    with patch.object(hass, "async_add_executor_job", side_effect=spy_executor) as spy:
        again = await frontend.async_card_url(hass)
    assert again == url
    assert not spy.called
