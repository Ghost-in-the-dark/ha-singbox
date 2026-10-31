"""Test fixtures for the sing-box integration."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL

from custom_components.singbox.const import CONF_UPDATE_INTERVAL

pytest_plugins = "pytest_homeassistant_custom_component"

MOCK_ENTRY_DATA = {
    CONF_HOST: "192.168.1.1",
    CONF_PORT: 9090,
    CONF_PASSWORD: "secret",
    CONF_SSL: False,
    CONF_UPDATE_INTERVAL: 5,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom integrations in all tests."""
    yield
