"""Config flow and options flow for the sing-box integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .backend import detect_backend
from .clash import ClashApiError
from .const import (
    CONF_HISTORY,
    CONF_PURGE_HISTORY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_HISTORY,
    DEFAULT_PORT,
    DEFAULT_PURGE_HISTORY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    UPDATE_INTERVAL_OPTIONS,
)
from .grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError

_LOGGER = logging.getLogger(__package__)

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
        vol.Required(CONF_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_SSL): BooleanSelector(),
        vol.Required(CONF_UPDATE_INTERVAL): SelectSelector(
            SelectSelectorConfig(
                options=[
                    {"label": f"{seconds} s", "value": str(seconds)}
                    for seconds in UPDATE_INTERVAL_OPTIONS
                ],
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


# The history toggle is a per-entry setting, so it is valid on first setup as
# well as in the options flow. Purging history is only offered for an existing
# entry: there is nothing recorded yet when the entry is first created.
HISTORY_SCHEMA: dict[Any, Any] = {
    vol.Optional(CONF_HISTORY, default=DEFAULT_HISTORY): BooleanSelector(),
}
OPTIONS_HISTORY_SCHEMA: dict[Any, Any] = {
    **HISTORY_SCHEMA,
    vol.Optional(CONF_PURGE_HISTORY, default=DEFAULT_PURGE_HISTORY): BooleanSelector(),
}


def _history_defaults(base: Mapping[str, Any]) -> dict[str, Any]:
    """Fill in the history flags, keeping them strictly boolean."""
    return {
        CONF_HISTORY: bool(base.get(CONF_HISTORY, DEFAULT_HISTORY)),
        CONF_PURGE_HISTORY: bool(base.get(CONF_PURGE_HISTORY, DEFAULT_PURGE_HISTORY)),
    }


def _default_values(user_input: dict[str, Any] | None) -> dict[str, Any]:
    """Suggested values for first-time setup (used to prefill the schema)."""
    if user_input:
        return {**user_input, **_history_defaults(user_input)}
    return {
        CONF_HOST: "",
        CONF_PORT: DEFAULT_PORT,
        CONF_PASSWORD: "",
        CONF_SSL: False,
        CONF_UPDATE_INTERVAL: str(DEFAULT_UPDATE_INTERVAL),
        **_history_defaults({}),
    }


def _current_values(config_entry: ConfigEntry) -> dict[str, Any]:
    """Effective values of a config entry (options override data)."""
    merged: dict[str, Any] = {**config_entry.data, **config_entry.options}
    return {
        **merged,
        CONF_UPDATE_INTERVAL: str(
            config_entry.options.get(
                CONF_UPDATE_INTERVAL,
                config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            )
        ),
        **_history_defaults(merged),
    }


async def _validate_connection(user_input: dict[str, Any]) -> dict[str, str]:
    """Check the entered connection settings.

    The client owns its own aiohttp session here (session=None), so it must be
    closed on *every* path: the previous layout returned from the except
    branches and leaked the session ("Unclosed client session" in the log).
    """
    client = None
    try:
        client, _backend = await detect_backend(
            host=user_input[CONF_HOST],
            port=int(user_input[CONF_PORT]),
            secret=user_input.get(CONF_PASSWORD, ""),
            use_tls=user_input.get(CONF_SSL, False),
            session=None,
        )
    except GrpcError as err:
        if err.status == GRPC_STATUS_UNAUTHENTICATED:
            return {"base": "invalid_auth"}
        _LOGGER.error("sing-box API error during validation: %s", err)
        return {"base": "cannot_connect"}
    except ClashApiError as err:
        if err.status == 401:
            return {"base": "invalid_auth"}
        _LOGGER.error("sing-box clash API error during validation: %s", err)
        return {"base": "cannot_connect"}
    except (TimeoutError, aiohttp.ClientError, OSError, ConnectionError) as err:
        _LOGGER.error("cannot connect to sing-box: %s", err)
        return {"base": "cannot_connect"}
    finally:
        if client is not None:
            await client.close()
    return {}


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """Coerce flow input into stored config entry values."""
    values: dict[str, Any] = {
        **user_input,
        # NumberSelector yields floats; ports must stay integers.
        CONF_PORT: int(user_input[CONF_PORT]),
        CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL]),
        # BooleanSelector can hand back a str/None from YAML-ish input; store bools.
        CONF_HISTORY: bool(user_input.get(CONF_HISTORY, DEFAULT_HISTORY)),
    }
    # purge_history exists only in the options flow; do not invent the key for
    # entries created by the first-time setup.
    if CONF_PURGE_HISTORY in user_input:
        values[CONF_PURGE_HISTORY] = bool(user_input[CONF_PURGE_HISTORY])
    return values


async def _async_purge_history(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the recorder history of this entry's entities.

    Purging is a convenience, never a requirement of saving the options: a
    missing recorder, an unloaded purge service or a recorder error must not
    surface to the user or roll the save back.
    """
    try:
        if "recorder" not in hass.config.components:
            return
        # purge_entities rejects a call without entity_id/domains/entity_globs,
        # so an entry whose entities are not registered yet is a no-op.
        entries = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        entity_ids = [item.entity_id for item in entries]
        if not entity_ids:
            return
        await hass.services.async_call(
            "recorder",
            "purge_entities",
            {"entity_id": entity_ids},
            blocking=True,
        )
        _LOGGER.debug(
            "Purged recorder history for %s entities of %s", len(entity_ids), entry.entry_id
        )
    except Exception:  # noqa: BLE001 - a failed purge must not break the save
        _LOGGER.debug("Failed to purge recorder history for %s", entry.entry_id, exc_info=True)


class SingBoxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sing-box."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate_connection(user_input)
            if not errors:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{int(user_input[CONF_PORT])}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"sing-box ({user_input[CONF_HOST]})",
                    data=_normalize(user_input),
                )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                CONNECTION_SCHEMA.extend(HISTORY_SCHEMA), _default_values(user_input)
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """Handle an authentication failure reported at runtime."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API secret."""
        errors: dict[str, str] = {}
        if user_input is not None:
            current = {
                **(self._get_reauth_entry().data or {}),
                **(self._get_reauth_entry().options or {}),
                CONF_PASSWORD: user_input.get(CONF_PASSWORD, ""),
            }
            errors = await _validate_connection(current)
            if not errors:
                entry = self._get_reauth_entry()
                # The runtime reads the secret with options overriding data, so a
                # secret saved by the options flow would shadow the new one. Drop
                # only that key: clearing all options (as before) also wiped the
                # settings owned by the options flow, e.g. history and interval.
                options = {
                    key: value for key, value in entry.options.items() if key != CONF_PASSWORD
                }
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_PASSWORD: user_input.get(CONF_PASSWORD, "")},
                    options=options,
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> SingBoxOptionsFlow:
        """Create the options flow."""
        return SingBoxOptionsFlow()


class SingBoxOptionsFlow(OptionsFlow):
    """Handle an options flow for sing-box.

    OptionsFlowWithConfigEntry is deprecated in Home Assistant core; the
    config entry is available as self.config_entry. A config entry update
    listener reloads the integration after the options change (see
    __init__.py).
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate_connection(user_input)
            if not errors:
                data = _normalize(user_input)
                result = self.async_create_entry(data=data)
                if data[CONF_PURGE_HISTORY]:
                    await _async_purge_history(self.hass, self.config_entry)
                return result
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                CONNECTION_SCHEMA.extend(OPTIONS_HISTORY_SCHEMA),
                _current_values(self.config_entry),
            ),
            errors=errors,
        )
