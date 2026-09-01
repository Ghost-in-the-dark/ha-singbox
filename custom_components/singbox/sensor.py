"""Sensor platform for the sing-box integration."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfDataRate,
    UnitOfInformation,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SingBoxCoordinator

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
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
        icon="mdi:upload-network-outline",
    ),
    SensorEntityDescription(
        key="downlink",
        translation_key="downlink",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfDataRate.BYTES_PER_SECOND,
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

# (entity key, attribute on SingBoxStatus, device_class override if any)
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


class SingBoxSensor(CoordinatorEntity[SingBoxCoordinator], SensorEntity):
    """Sensor reading a field from the coordinator snapshot."""

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
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="sing-box",
            manufacturer=MANUFACTURER,
            model=coordinator.data.version,
        )

    @property
    def native_value(self) -> object:
        value = getattr(self.coordinator.data, self._attr)
        if self._attr == "started_at" and value:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        return value

    @property
    def available(self) -> bool:
        return (
            super().available
            and getattr(self.coordinator.data, self._attr) is not None
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SingBoxCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SingBoxSensor(coordinator, description, _SENSOR_ATTRS[description.key])
        for description in SENSOR_DESCRIPTIONS
    )
