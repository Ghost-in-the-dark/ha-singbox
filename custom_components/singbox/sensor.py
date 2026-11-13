"""Sensor platform for the sing-box integration."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfDataRate,
    UnitOfInformation,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .backend import BACKEND_GRPC
from .const import DOMAIN, MANUFACTURER
from .coordinator import SingBoxCoordinator

_LOGGER = logging.getLogger(__package__)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="version",
        translation_key="version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:information-outline",
    ),
    SensorEntityDescription(
        key="api_version",
        translation_key="api_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:code-json",
    ),
    SensorEntityDescription(
        key="started_at",
        translation_key="started_at",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
    ),
    SensorEntityDescription(
        key="memory",
        translation_key="memory",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        icon="mdi:memory",
    ),
    SensorEntityDescription(
        key="goroutines",
        translation_key="goroutines",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:chart-timeline-variant",
    ),
    SensorEntityDescription(
        key="connections_in",
        translation_key="connections_in",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lan-connect",
    ),
    SensorEntityDescription(
        key="connections_out",
        translation_key="connections_out",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lan-disconnect",
    ),
    SensorEntityDescription(
        key="uplink",
        translation_key="uplink",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        icon="mdi:upload-network-outline",
    ),
    SensorEntityDescription(
        key="downlink",
        translation_key="downlink",
        device_class=SensorDeviceClass.DATA_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        suggested_unit_of_measurement=UnitOfDataRate.KIBIBYTES_PER_SECOND,
        icon="mdi:download-network-outline",
    ),
    SensorEntityDescription(
        key="uplink_total",
        translation_key="uplink_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        icon="mdi:upload-network-outline",
    ),
    SensorEntityDescription(
        key="downlink_total",
        translation_key="downlink_total",
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        icon="mdi:download-network-outline",
    ),
)

# Fields the clash API cannot report at all.
_GRPC_ONLY = frozenset({"api_version", "goroutines", "connections_out"})

# (entity key, attribute on SingBoxStatus)
_SENSOR_ATTRS: dict[str, str] = {
    "version": "version",
    "api_version": "api_version",
    "started_at": "started_at",
    "memory": "memory",
    "goroutines": "goroutines",
    "connections_in": "connections_in",
    "connections_out": "connections_out",
    "uplink": "uplink",
    "downlink": "downlink",
    "uplink_total": "uplink_total",
    "downlink_total": "downlink_total",
}


def device_info(coordinator: SingBoxCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name="sing-box",
        manufacturer=MANUFACTURER,
        model=coordinator.data.version,
    )


class SingBoxSensor(CoordinatorEntity[SingBoxCoordinator], SensorEntity):
    """Sensor reading a field from the coordinator snapshot."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SingBoxCoordinator,
        description: SensorEntityDescription,
        attr: str,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr = attr
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = device_info(coordinator)

    @property
    def native_value(self) -> object:
        value = getattr(self.coordinator.data, self._attr)
        if self._attr == "started_at" and value:
            return datetime.fromtimestamp(value / 1000, tz=UTC)
        return value

    @property
    def available(self) -> bool:
        # goroutines / connections_out / api_version only exist on the gRPC
        # backend; creating them unconditionally left permanently unavailable
        # entities on every clash_api-only install.
        if self._attr in _GRPC_ONLY and self.coordinator.backend != BACKEND_GRPC:
            return False
        return super().available and getattr(self.coordinator.data, self._attr) is not None


class SingBoxPingSensor(CoordinatorEntity[SingBoxCoordinator], SensorEntity):
    """Sensor showing the last url-test delay (ping) of a single proxy."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:heart-pulse"
    # Grouped as diagnostics so they stay out of the default dashboard and
    # the entity list's primary view. They must stay *enabled*: the
    # companion Sing-box Panel Card reads their state for the per-node ping
    # chips, and a disabled entity has no state at all (every chip would
    # render as "—"). Excluding them from the recorder is the recommended
    # way to keep the database small (see README).
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SingBoxCoordinator, tag: str) -> None:
        super().__init__(coordinator)
        self._tag = tag
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_ping_{tag}"
        self._attr_name = tag
        self._attr_device_info = device_info(coordinator)

    @property
    def proxy(self):
        return self.coordinator.proxy(self._tag)

    @property
    def native_value(self) -> int | None:
        proxy = self.proxy
        if proxy is None or proxy.url_test_delay <= 0:
            return None
        return proxy.url_test_delay

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        proxy = self.proxy
        if proxy is None:
            return {}
        attributes: dict[str, Any] = {}
        if proxy.url_test_time > 0:
            attributes["last_checked"] = datetime.fromtimestamp(
                proxy.url_test_time / 1000, tz=UTC
            ).isoformat()
        # A failed test is a real answer and has to be distinguishable from
        # "never tested": both end up with state None (no delay to report,
        # and a numeric 0 would lie about the ping), so the flag is what the
        # card paints red. Only present when there is something to say.
        if proxy.url_test_failed:
            attributes["last_test_failed"] = True
        return attributes

    @property
    def available(self) -> bool:
        return super().available and self.proxy is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SingBoxCoordinator = hass.data[DOMAIN][entry.entry_id]

    # The status sensors are gauges: a handful of them, updating on the
    # configured interval. They are created either way.
    async_add_entities(
        SingBoxSensor(coordinator, description, _SENSOR_ATTRS[description.key])
        for description in SENSOR_DESCRIPTIONS
    )

    # The ping sensors are a different animal: one per outbound (a few dozen
    # on a realistic subscription), each written on every url-test. They are
    # what makes the recorder grow, and they are also the reason the card
    # used to be the only place that knew a test had failed.
    #
    # With history enabled they are created exactly as before - the card and
    # every existing dashboard keep reading them, so nothing changes for
    # current users. With history disabled they are not created at all: the
    # card gets the same numbers from the singbox/status websocket command
    # (which reads the coordinator, not the recorder), so the only thing that
    # is lost is the log of past delays - which is precisely what the option
    # promises, because Home Assistant has no per-entity "do not record" flag
    # (see the HISTORY option documentation).
    if not coordinator.history_enabled:
        _LOGGER.debug("state history is disabled; not creating ping sensors")
        return

    # Proxies are discovered dynamically: sing-box may add outbounds (or the
    # group stream may deliver them later), and entities for the ones known at
    # setup time only would otherwise require a Home Assistant restart.
    # Seed the known set from the entity registry, not from an empty set.
    # Starting empty made the stale sweep below useless after a restart: the
    # sensors created by a previous run are in the registry but never in
    # "known", so a tag that disappeared while Home Assistant was down left
    # its entity in the registry forever (state unavailable). That is exactly
    # the pile of orphaned sing_box_*_out sensors a subscription change leaves
    # behind, and it survived every restart.
    # Two different sets, and they must not be confused:
    #
    # * "known" is what this run of the platform has created. Entities are
    #   objects owned by the platform, so an entity that a previous run put in
    #   the registry still has to be created again here - seeding "known" from
    #   the registry made every ping sensor skip creation on restart and left
    #   the whole set permanently unavailable.
    # * "previous" is what the registry says existed. It is only used to find
    #   tags that disappeared from the server while Home Assistant was down,
    #   which otherwise leave an unavailable entity behind forever.
    known: set[str] = set()
    unique_prefix = f"{coordinator.config_entry.entry_id}_ping_"
    entity_registry = er.async_get(hass)
    previous: set[str] = set()
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry, coordinator.config_entry.entry_id
    ):
        if registry_entry.domain != "sensor" or not registry_entry.unique_id.startswith(
            unique_prefix
        ):
            continue
        previous.add(registry_entry.unique_id[len(unique_prefix) :])

    @callback
    def _add_new_proxies() -> None:
        # A proxy that disappears from the server must disappear from Home
        # Assistant too. Previously only additions were handled, so every
        # subscription refresh that dropped or renamed an outbound left a
        # permanently "unavailable" sensor behind - one dead entity per removed
        # node, forever, with the old unique_id blocking a clean recreation if
        # the tag ever came back.
        current = {proxy.tag for proxy in coordinator.data.proxies}
        # Only tags the registry knows about can have a stale entity to drop;
        # anything this run created is in "known" and is handled below.
        stale = (previous - current) - known
        if stale:
            previous.difference_update(stale)
            _LOGGER.debug("removing ping sensors for %s", ", ".join(sorted(stale)))
            # Keep the entity registry in step with what the server reports.
            for tag in stale:
                unique_id = f"{coordinator.config_entry.entry_id}_ping_{tag}"
                entity_id = entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id)
                if entity_id is not None:
                    entity_registry.async_remove(entity_id)
        new_tags = [tag for tag in current if tag not in known]
        if not new_tags:
            return
        known.update(new_tags)
        _LOGGER.debug("adding ping sensors for %s", ", ".join(new_tags))
        async_add_entities(
            (SingBoxPingSensor(coordinator, tag) for tag in new_tags),
            update_before_add=False,
        )

    _add_new_proxies()
    coordinator.async_add_discovery_listener(_add_new_proxies)
    entry.async_on_unload(lambda: coordinator.async_remove_discovery_listener(_add_new_proxies))
