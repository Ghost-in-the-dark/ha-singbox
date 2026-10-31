"""Select platform for the sing-box integration.

Creates one select entity per outbound group and, when the backend reports
clash modes, one select for the clash mode.
"""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SingBoxCoordinator

_LOGGER = logging.getLogger(__package__)


def device_info(coordinator: SingBoxCoordinator) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name="sing-box",
        manufacturer=MANUFACTURER,
        model=coordinator.data.version,
    )


class SingBoxGroupSelect(CoordinatorEntity[SingBoxCoordinator], SelectEntity):
    """Select entity for a sing-box outbound group."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SingBoxCoordinator, group_tag: str) -> None:
        super().__init__(coordinator)
        self._group_tag = group_tag
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_group_{group_tag}"
        self._attr_name = group_tag
        self._attr_device_info = device_info(coordinator)

    @property
    def options(self) -> list[str]:
        group = self.coordinator.group(self._group_tag)
        return [item.tag for item in group.items] if group else []

    @property
    def current_option(self) -> str | None:
        group = self.coordinator.group(self._group_tag)
        return group.selected if group else None

    @property
    def available(self) -> bool:
        group = self.coordinator.group(self._group_tag)
        return super().available and group is not None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.select_outbound(self._group_tag, option)


class SingBoxClashModeSelect(CoordinatorEntity[SingBoxCoordinator], SelectEntity):
    """Select entity for the sing-box clash mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "clash_mode"

    def __init__(self, coordinator: SingBoxCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_clash_mode"
        self._attr_device_info = device_info(coordinator)

    @property
    def options(self) -> list[str]:
        return self.coordinator.data.clash_mode_list or []

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data.clash_mode

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.set_clash_mode(option)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SingBoxCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[str] = set()
    mode_added = False

    @callback
    def _add_new_entities() -> None:
        nonlocal mode_added
        entities: list[SelectEntity] = []
        for group in coordinator.data.groups:
            if not group.selectable or group.tag in known:
                continue
            known.add(group.tag)
            entities.append(SingBoxGroupSelect(coordinator, group.tag))
        if not mode_added and coordinator.clash_mode_available:
            mode_added = True
            entities.append(SingBoxClashModeSelect(coordinator))
        if entities:
            _LOGGER.debug("adding %s select entities", len(entities))
            async_add_entities(entities, update_before_add=False)

    # Groups are discovered dynamically (gRPC SubscribeGroups / clash /proxies
    # can deliver them after setup, and sing-box may gain groups on reload).
    _add_new_entities()
    coordinator.async_add_discovery_listener(_add_new_entities)
    entry.async_on_unload(lambda: coordinator.async_remove_discovery_listener(_add_new_entities))
