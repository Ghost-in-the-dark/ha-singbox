"""Constants for the sing-box integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "singbox"
MANUFACTURER = "SagerNet"

PLATFORMS = [Platform.SENSOR, Platform.SELECT]

DEFAULT_PORT = 9090

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 1  # seconds
UPDATE_INTERVAL_OPTIONS = [1, 2, 5, 10, 30, 60]

# SubscribeStatus interval is a Go time.Duration on the server, i.e.
# nanoseconds; the coordinator computes the value from the configured seconds.
