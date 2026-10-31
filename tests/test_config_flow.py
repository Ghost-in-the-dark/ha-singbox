"""Tests for the sing-box config and options flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.singbox.backend import BACKEND_CLASH
from custom_components.singbox.const import DOMAIN
from custom_components.singbox.grpc import GRPC_STATUS_UNAUTHENTICATED, GrpcError

from .conftest import MOCK_ENTRY_DATA

USER_INPUT = {
    CONF_HOST: "192.168.1.1",
    CONF_PORT: "9090",
    CONF_PASSWORD: "secret",
    "ssl": False,
    "update_interval": "5",
}


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """A valid connection creates the entry."""
    with patch(
        "custom_components.singbox.config_flow.detect_backend",
        new=AsyncMock(return_value=(AsyncMock(), BACKEND_CLASH)),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PORT] == 9090
    assert result["data"]["update_interval"] == 5


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (GrpcError(GRPC_STATUS_UNAUTHENTICATED), "invalid_auth"),
        (GrpcError(2, "boom"), "cannot_connect"),
        (ConnectionError("no route"), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
    ],
)
async def test_user_flow_errors(hass: HomeAssistant, error: Exception, expected: str) -> None:
    """Connection failures are reported as form errors."""
    with patch(
        "custom_components.singbox.config_flow.detect_backend",
        new=AsyncMock(side_effect=error),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


async def test_validate_connection_closes_client(hass: HomeAssistant) -> None:
    """The validation client is closed even when the backend rejects auth."""
    from custom_components.singbox import config_flow

    client = AsyncMock()
    with patch(
        "custom_components.singbox.config_flow.detect_backend",
        new=AsyncMock(side_effect=GrpcError(GRPC_STATUS_UNAUTHENTICATED)),
    ):
        errors = await config_flow._validate_connection(USER_INPUT)
    assert errors == {"base": "invalid_auth"}

    with patch(
        "custom_components.singbox.config_flow.detect_backend",
        new=AsyncMock(return_value=(client, BACKEND_CLASH)),
    ):
        errors = await config_flow._validate_connection(USER_INPUT)
    assert errors == {}
    client.close.assert_awaited_once()


async def test_options_flow_updates_entry(hass: HomeAssistant) -> None:
    """Options are stored and the entry reloads."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA, options={}, entry_id="test")
    entry.add_to_hass(hass)
    with patch(
        "custom_components.singbox.config_flow.detect_backend",
        new=AsyncMock(return_value=(AsyncMock(), BACKEND_CLASH)),
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {**USER_INPUT, "update_interval": "10"}
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["update_interval"] == 10


async def test_reauth_flow_updates_secret(hass: HomeAssistant) -> None:
    """A reauth flow replaces the stored secret."""
    entry = MockConfigEntry(domain=DOMAIN, data=MOCK_ENTRY_DATA, options={}, entry_id="reauth")
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    with patch(
        "custom_components.singbox.config_flow.detect_backend",
        new=AsyncMock(return_value=(AsyncMock(), BACKEND_CLASH)),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new-secret"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-secret"
