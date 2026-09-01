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

# Display unit for the uplink/downlink speed sensors. The stored value is the
# unit string itself; the sensor scales the raw B/s value by the matching
# factor.
CONF_SPEED_UNIT = "speed_unit"
DEFAULT_SPEED_UNIT = "B/s"
SPEED_UNIT_OPTIONS = ["B/s", "KiB/s", "kB/s", "MiB/s", "MB/s"]
SPEED_UNIT_FACTORS = {
    "B/s": 1.0,
    "KiB/s": 1 / 1024,
    "kB/s": 1 / 1000,
    "MiB/s": 1 / 1024**2,
    "MB/s": 1 / 1000**2,
}

# SubscribeStatus interval is a Go time.Duration on the server, i.e.
# nanoseconds; the coordinator computes the value from the configured seconds.
