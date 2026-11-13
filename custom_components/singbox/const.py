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

# State history (the recorder database).
#
# Every url-test writes a new state to each ping sensor, and the integration
# creates one ping sensor per outbound plus one select per group: on a
# realistic setup that is the bulk of everything the integration ever sends to
# the recorder. Making it optional is the difference between a database that
# grows by megabytes per day and one that barely moves, so the user gets to
# decide. Turning it off does not change what the dashboard shows: the ping
# sensors are still created and still carry the current delay, they are just
# not written to the recorder, and the panel card reads the live values over
# its own websocket command instead of from history.
CONF_HISTORY = "history"
DEFAULT_HISTORY = True
# One-shot option: delete whatever was already recorded for this entry. Only
# offered in the options flow, because it makes no sense on first setup.
CONF_PURGE_HISTORY = "purge_history"
DEFAULT_PURGE_HISTORY = False

# Enable "write history" only for this subset of entities, keyed by the entity
# description key. Live gauges (speed, memory, counts) are exactly what the
# recorder is for; the diagnostic identity values never change and would only
# add a single row each.
HISTORY_SENSOR_KEYS = frozenset(
    {
        "memory",
        "connections_in",
        "uplink",
        "downlink",
        "uplink_total",
        "downlink_total",
    }
)


# SubscribeStatus interval is a Go time.Duration on the server, i.e.
# nanoseconds; the coordinator computes the value from the configured seconds.
