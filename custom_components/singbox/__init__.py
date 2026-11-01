"""sing-box integration for Home Assistant.

Connects to a running sing-box instance through its gRPC ``api`` service
(sing-box >= 1.14.0) over gRPC-Web, falling back to the ``clash_api`` REST
API on older builds, and exposes live status sensors plus outbound group
selectors.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .backend import detect_backend
from .clash import ClashApiError, is_auth_error
from .const import (
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import SingBoxCoordinator
from .errors import SingBoxAuthError, SingBoxNotSupported
from .frontend import async_register_card
from .grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError

_LOGGER = logging.getLogger(__package__)

DATA_WS_REGISTERED = "singbox_websocket_registered"

SERVICE_NAMES = (
    "select_outbound",
    "url_test",
    "set_group_expand",
    "close_connection",
    "close_all_connections",
    "set_clash_mode",
)


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the sing-box component.

    The bundled Lovelace card is registered here, not in async_setup_entry:
    the card has to be available as soon as the integration is installed,
    even while a config entry is still failing (unreachable sing-box host,
    missing secret). Registering it from async_setup_entry meant the card
    silently disappeared whenever the entry did not reach LOADED, which is
    exactly the `Custom element doesn't exist` case. The manifest declares
    `http` and `frontend` as dependencies, so both are ready here.
    """
    await async_register_card(hass)
    _async_register_websocket_api(hass)
    return True


def _async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register the panel card's data endpoints (idempotent).

    Registered from async_setup rather than async_setup_entry so the card can
    always talk to the integration, even while an entry is failing to load:
    the UI then gets a clear answer instead of "unknown_command".
    """
    if hass.data.get(DATA_WS_REGISTERED):
        return
    websocket_api.async_register_command(hass, ws_connections)
    hass.data[DATA_WS_REGISTERED] = True


def _select_coordinator(hass: HomeAssistant, entry_id: str | None) -> SingBoxCoordinator:
    """Resolve the coordinator for a websocket request.

    An unknown or not-yet-loaded entry raises ConfigEntryError, which the
    command turns into a "not found" error for the card.
    """
    coordinators: dict[str, SingBoxCoordinator] = hass.data.get(DOMAIN, {})
    if entry_id is not None:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise ConfigEntryError(f"No sing-box config entry with id {entry_id}")
        return coordinator
    loaded = [item for item in coordinators.values() if isinstance(item, SingBoxCoordinator)]
    if not loaded:
        raise ConfigEntryError("No sing-box config entry is loaded")
    return loaded[0]


@websocket_api.websocket_command(
    {
        vol.Required("type"): "singbox/connections",
        vol.Optional("entry_id"): cv.string,
    }
)
@websocket_api.async_response
async def ws_connections(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Return the live sing-box connections for the panel card.

    Payload::

        {
          "connections": [
            {"id": "...", "network": "tcp", "protocol": "https",
             "source": "192.168.1.5:51234", "destination": "1.2.3.4:443",
             "host": "example.com", "rule": "...", "outbound": "proxy",
             "chain": ["proxy", "hk"], "process": "curl",
             "upload": 1234, "download": 5678,
             "upload_total": 100000, "download_total": 200000,
             "created_at": 1730000000000}
          ],
          "count": 1,
          "supported": true
        }

    ``supported`` is False when the backend cannot report connections at all
    (connection tracking disabled, or an API without SubscribeConnections);
    the card then shows a hint instead of an empty list.
    """
    try:
        coordinator = _select_coordinator(hass, msg.get("entry_id"))
    except ConfigEntryError as err:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(err))
        return
    connections = [item.as_dict() for item in coordinator.connections]
    connection.send_result(
        msg["id"],
        {
            "connections": connections,
            "count": len(connections),
            "supported": coordinator.connections_supported,
        },
    )


def _translate_setup_error(err: Exception) -> Exception:
    """Map a setup failure to the exception Home Assistant understands.

    ConfigEntryAuthFailed triggers the reauth flow, ConfigEntryNotReady asks
    Home Assistant to retry with backoff. Anything else stays as-is so a real
    bug is not silently retried forever.
    """
    if isinstance(err, SingBoxAuthError):
        return ConfigEntryAuthFailed(f"sing-box API authentication failed: {err}")
    if isinstance(err, GrpcError):
        if err.status == GRPC_STATUS_UNAUTHENTICATED:
            return ConfigEntryAuthFailed(f"sing-box API authentication failed: {err}")
        return ConfigEntryNotReady(f"sing-box API error: {err}")
    if isinstance(err, ClashApiError):
        if err.status == 401 or is_auth_error(err):
            return ConfigEntryAuthFailed(f"sing-box clash API authentication failed: {err}")
        return ConfigEntryNotReady(f"sing-box clash API error: {err}")
    if isinstance(err, (OSError, ConnectionError, TimeoutError)):
        return ConfigEntryNotReady(f"cannot reach sing-box API: {err}")
    return err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a sing-box config entry."""
    # Options (set via the options flow) override the initial data.
    host = entry.options.get(CONF_HOST, entry.data[CONF_HOST])
    port = int(entry.options.get(CONF_PORT, entry.data[CONF_PORT]))
    secret = entry.options.get(CONF_PASSWORD, entry.data.get(CONF_PASSWORD, ""))
    use_tls = entry.options.get(CONF_SSL, entry.data.get(CONF_SSL, False))
    update_interval = int(
        entry.options.get(
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
    )
    session = async_get_clientsession(hass)
    # Backend detection must run inside the try block: it performs the first
    # network call, so an unreachable host or a wrong secret surfaces here
    # (not in coordinator.async_setup). Escaping as a raw error left the
    # entry in a failed state that Home Assistant never retried and never
    # offered to re-authenticate.
    coordinator: SingBoxCoordinator | None = None
    try:
        client, backend = await detect_backend(host, port, secret, use_tls, session)
        coordinator = SingBoxCoordinator(
            hass, entry, client, backend, update_interval_seconds=update_interval
        )
        await coordinator.async_setup()
    except Exception as err:
        # Never leak a half-initialised coordinator (streams, backend session).
        if coordinator is not None:
            await coordinator.async_shutdown()
        raise _translate_setup_error(err) from err
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_setup_services(hass, entry)
    # Reload the integration when options (host/port/secret/interval) change.
    entry.async_on_unload(entry.add_update_listener(_async_update_options))
    return True


async def _async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry after its options were updated."""
    # ConfigEntries exposes async_reload(entry_id); async_reload_entry() does
    # not exist, so saving the options raised AttributeError inside the update
    # listener and the entry was never reloaded.
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a sing-box config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: SingBoxCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()
        if not any(isinstance(item, SingBoxCoordinator) for item in hass.data[DOMAIN].values()):
            # The services resolve their coordinator from hass.data, so they
            # must not outlive the last entry. The bundled card is deliberately
            # NOT unregistered here: it is registered from async_setup, which
            # runs once per process, so unloading (or reloading) an entry must
            # not strand the dashboards with a missing element.
            for name in SERVICE_NAMES:
                if hass.services.has_service(DOMAIN, name):
                    hass.services.async_remove(DOMAIN, name)
    return unload_ok


async def _async_setup_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register the sing-box services (idempotent)."""
    if hass.services.has_service(DOMAIN, "select_outbound"):
        return

    def _entries(call: ServiceCall) -> list[SingBoxCoordinator]:
        entry_id = call.data.get("entry_id")
        if entry_id is not None:
            coordinator = hass.data[DOMAIN].get(entry_id)
            if coordinator is None:
                raise ServiceValidationError(f"No sing-box config entry with id {entry_id}")
            return [coordinator]
        coordinators = [
            item
            for item in hass.data.get(DOMAIN, {}).values()
            if isinstance(item, SingBoxCoordinator)
        ]
        if not coordinators:
            raise ServiceValidationError("No sing-box config entry is loaded")
        if len(coordinators) != 1:
            raise ServiceValidationError("Multiple sing-box entries configured; specify entry_id")
        return coordinators

    async def _select_outbound(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.select_outbound(call.data["group_tag"], call.data["outbound_tag"])

    async def _url_test(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.url_test(call.data["outbound_tag"], call.data.get("url"))

    async def _set_group_expand(call: ServiceCall) -> None:
        for coordinator in _entries(call):
            await coordinator.set_group_expand(call.data["group_tag"], call.data["is_expand"])

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
            except SingBoxNotSupported as err:
                raise ServiceValidationError(str(err)) from err
            except SingBoxAuthError as err:
                if entry is not None:
                    entry.async_start_reauth(hass)
                raise HomeAssistantError(f"sing-box authentication failed: {err}") from err
            except (ClashApiError, GrpcError) as err:
                if is_auth_error(err) and entry is not None:
                    entry.async_start_reauth(hass)
                raise HomeAssistantError(f"sing-box API error: {err}") from err
            except (OSError, ConnectionError, TimeoutError) as err:
                raise HomeAssistantError(f"cannot reach the sing-box API: {err}") from err

        return _inner

    services = {
        "select_outbound": (_select_outbound, {"group_tag": cv.string, "outbound_tag": cv.string}),
        "url_test": (_url_test, {"outbound_tag": cv.string, vol.Optional("url"): cv.url}),
        "set_group_expand": (_set_group_expand, {"group_tag": cv.string, "is_expand": cv.boolean}),
        "close_connection": (_close_connection, {"connection_id": cv.string}),
        "close_all_connections": (_close_all_connections, {}),
        "set_clash_mode": (_set_clash_mode, {"mode": cv.string}),
    }
    for name, (handler, fields) in services.items():
        # These are config-entry level services, not entity services: do not
        # require an entity/device target (that made calls from the Lovelace
        # card fail with "must contain at least one of entity_id, ...").
        # ALLOW_EXTRA keeps compatibility with callers that still pass an
        # entity_id target (e.g. the panel card) — a plain vol.Schema would
        # reject them with "extra keys not allowed".
        hass.services.async_register(
            DOMAIN, name, _wrap(handler), schema=vol.Schema(fields, extra=vol.ALLOW_EXTRA)
        )
