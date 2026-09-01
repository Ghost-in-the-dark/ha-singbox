"""sing-box integration for Home Assistant.

Connects to the sing-box ``api`` service (sing-box >= 1.14.0) over gRPC-Web
and exposes live status sensors plus outbound group selectors.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SingBoxCoordinator
from .grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError, SingBoxClient

_LOGGER = logging.getLogger(__package__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the sing-box component (config flow only)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a sing-box config entry."""
    # Options (set via the options flow) override the initial data.
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    port = entry.options.get(CONF_PORT, entry.data[CONF_PORT])
    secret = entry.options.get(CONF_PASSWORD, entry.data.get(CONF_PASSWORD, ""))
    use_tls = entry.options.get(CONF_SSL, entry.data.get(CONF_SSL, False))
    update_interval = int(
        entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
    )
    client = SingBoxClient(
        host=host,
        port=port,
        secret=secret,
        use_tls=use_tls,
        session=async_get_clientsession(hass),
    )
    coordinator = SingBoxCoordinator(
        hass, entry, client, update_interval_seconds=update_interval
    )
    try:
        await coordinator.async_setup()
    except GrpcError as err:
        if err.status == GRPC_STATUS_UNAUTHENTICATED:
            raise ConfigEntryAuthFailed(
                f"sing-box API authentication failed: {err}"
            ) from err
        raise ConfigEntryNotReady(f"sing-box API error: {err}") from err
    except (OSError, ConnectionError) as err:
        raise ConfigEntryNotReady(f"cannot reach sing-box API: {err}") from err
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_setup_services(hass)
    # Reload the integration when options (host/port/secret/interval) change.
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its options were updated."""
    await hass.config_entries.async_reload_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a sing-box config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SingBoxCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
    return unload_ok


async def _async_setup_services(hass: HomeAssistant) -> None:
    """Register the sing-box services (idempotent)."""
    if hass.services.has_service(DOMAIN, "select_outbound"):
        return

    def _entries(call: ServiceCall) -> list[SingBoxCoordinator]:
        entry_id = call.data.get("entry_id")
        if entry_id is not None:
            coordinator = hass.data[DOMAIN].get(entry_id)
            if coordinator is None:
                raise ServiceValidationError(
                    f"No sing-box config entry with id {entry_id}"
                )
            return [coordinator]
        coordinators = list(hass.data.get(DOMAIN, {}).values())
        if len(coordinators) != 1:
            raise ServiceValidationError(
                "Multiple sing-box entries configured; specify entry_id"
            )
        return coordinators

    async def _select_outbound(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.select_outbound(
                call.data["group_tag"], call.data["outbound_tag"]
            )

    async def _url_test(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.url_test(call.data["outbound_tag"])

    async def _set_group_expand(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.set_group_expand(
                call.data["group_tag"], call.data["is_expand"]
            )

    async def _close_connection(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.close_connection(call.data["connection_id"])

    async def _close_all_connections(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.close_all_connections()

    async def _set_clash_mode(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.set_clash_mode(call.data["mode"])

    def _wrap(fn):
        async def _inner(call: ServiceCall) -> None:
            try:
                await fn(call)
            except (OSError, ConnectionError) as err:
                raise HomeAssistantError(f"sing-box API error: {err}") from err

        return _inner

    services = {
        "select_outbound": (_select_outbound, {"group_tag": cv.string, "outbound_tag": cv.string}),
        "url_test": (_url_test, {"outbound_tag": cv.string}),
        "set_group_expand": (_set_group_expand, {"group_tag": cv.string, "is_expand": cv.boolean}),
        "close_connection": (_close_connection, {"connection_id": cv.string}),
        "close_all_connections": (_close_all_connections, {}),
        "set_clash_mode": (_set_clash_mode, {"mode": cv.string}),
    }
    for name, (handler, fields) in services.items():
        hass.services.async_register(
            DOMAIN, name, _wrap(handler), schema=cv.make_entity_service_schema(fields)
        )
