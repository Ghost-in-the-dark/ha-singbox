"""Constants for the sing-box integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "singbox"
MANUFACTURER = "SagerNet"

PLATFORMS = [Platform.SENSOR, Platform.SELECT]

DEFAULT_PORT = 9090

# SubscribeStatus interval in nanoseconds (Go time.Duration on the server);
# 1_000_000_000 ns == 1 s.
STATUS_INTERVAL_NS = 1_000_000_000
