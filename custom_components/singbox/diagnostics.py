"""Diagnostics support for the sing-box integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SSL
from homeassistant.core import HomeAssistant

from .const import CONF_UPDATE_INTERVAL, DOMAIN

TO_REDACT = {CONF_PASSWORD}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "settings": {
            CONF_HOST: entry.options.get(CONF_HOST, entry.data.get(CONF_HOST)),
            CONF_PORT: entry.options.get(CONF_PORT, entry.data.get(CONF_PORT)),
            CONF_SSL: entry.options.get(CONF_SSL, entry.data.get(CONF_SSL, False)),
            CONF_UPDATE_INTERVAL: coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "backend": {
            "type": coordinator.backend,
            "version": data.version,
            "api_version": data.api_version,
            "clash_mode_available": coordinator.clash_mode_available,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "stream_tasks": len(coordinator.stream_tasks),
            "stream_tasks_running": sum(1 for task in coordinator.stream_tasks if not task.done()),
        },
        "status": {
            "memory": data.memory,
            "goroutines": data.goroutines,
            "connections_in": data.connections_in,
            "connections_out": data.connections_out,
            "traffic_available": data.traffic_available,
            "uplink": data.uplink,
            "downlink": data.downlink,
            "uplink_total": data.uplink_total,
            "downlink_total": data.downlink_total,
            "clash_mode": data.clash_mode,
            "clash_mode_list": data.clash_mode_list,
        },
        "groups": [
            {
                "tag": group.tag,
                "type": group.type,
                "selectable": group.selectable,
                "selected": group.selected,
                "items": [item.tag for item in group.items],
            }
            for group in data.groups
        ],
        "proxies": [
            {
                "tag": proxy.tag,
                "type": proxy.type,
                "url_test_delay": proxy.url_test_delay,
                "url_test_time": proxy.url_test_time,
            }
            for proxy in data.proxies
        ],
    }
