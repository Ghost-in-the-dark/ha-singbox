"""Config flow for the sing-box integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import DEFAULT_PORT, DOMAIN
from .grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError, SingBoxClient

_LOGGER = logging.getLogger(__package__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT)
        ),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
            NumberSelectorConfig(
                min=1, max=65535, mode=NumberSelectorMode.BOX
            )
        ),
        vol.Optional(CONF_PASSWORD, default=""): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_SSL, default=False): BooleanSelector(),
    }
)


class SingBoxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for sing-box."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors = await self._validate_connection(user_input)
            if not errors:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"sing-box ({user_input[CONF_HOST]})", data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def _validate_connection(
        self, user_input: dict[str, Any]
    ) -> dict[str, str]:
        client = SingBoxClient(
            host=user_input[CONF_HOST],
            port=user_input[CONF_PORT],
            secret=user_input[CONF_PASSWORD],
            use_tls=user_input[CONF_SSL],
        )
        try:
            await client.get_version()
        except GrpcError as err:
            if err.status == GRPC_STATUS_UNAUTHENTICATED:
                return {"base": "invalid_auth"}
            _LOGGER.error("sing-box API error during validation: %s", err)
            return {"base": "cannot_connect"}
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ConnectionError) as err:
            _LOGGER.error("cannot connect to sing-box: %s", err)
            return {"base": "cannot_connect"}
        finally:
            await client.close()
        return {}
