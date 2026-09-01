"""Config flow and options flow for the sing-box integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithConfigEntry,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL
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
    CONF_UPDATE_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    UPDATE_INTERVAL_OPTIONS,
)
from .grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError

_LOGGER = logging.getLogger(__package__)

CONNECTION_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
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


def _default_values(user_input: dict[str, Any] | None) -> dict[str, Any]:
    """Suggested values for first-time setup (used to prefill the schema)."""
    return user_input or {
        CONF_HOST: "",
        CONF_PORT: DEFAULT_PORT,
        CONF_PASSWORD: "",
        CONF_SSL: False,
        CONF_UPDATE_INTERVAL: str(DEFAULT_UPDATE_INTERVAL),
    }


def _current_values(config_entry: ConfigEntry) -> dict[str, Any]:
    """Effective values of a config entry (options override data)."""
    return {
        **config_entry.data,
        **config_entry.options,
        CONF_UPDATE_INTERVAL: str(
            config_entry.options.get(
                CONF_UPDATE_INTERVAL,
                config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            )
        ),
    }


async def _validate_connection(user_input: dict[str, Any]) -> dict[str, str]:
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
    except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ConnectionError) as err:
        _LOGGER.error("cannot connect to sing-box: %s", err)
        return {"base": "cannot_connect"}
    await client.close()
    return {}


def _normalize(user_input: dict[str, Any]) -> dict[str, Any]:
    """Coerce flow input into stored config entry values."""
    return {
        **user_input,
        # NumberSelector yields floats; ports must stay integers.
        CONF_PORT: int(user_input[CONF_PORT]),
        CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL]),
    }


class SingBoxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sing-box."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
                CONNECTION_SCHEMA, _default_values(user_input)
            ),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> SingBoxOptionsFlow:
        """Create the options flow."""
        return SingBoxOptionsFlow(config_entry)


class SingBoxOptionsFlow(OptionsFlowWithConfigEntry):
    """Handle an options flow for sing-box.

    A config entry update listener reloads the integration after the options
    change (see __init__.py).
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await _validate_connection(user_input)
            if not errors:
                return self.async_create_entry(data=_normalize(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                CONNECTION_SCHEMA, _current_values(self.config_entry)
            ),
            errors=errors,
        )
