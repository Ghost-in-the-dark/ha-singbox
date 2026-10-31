"""Serve and register the bundled Sing-box Panel Card.

A card that depends 1:1 on an integration should ship inside it instead of
living in a separate repository.

The file is served from an integration static route and registered with
Lovelace as a module resource. That is deliberate: it is the only mechanism
that works on every frontend build.

Home Assistant ships two frontend builds. The modern one is loaded when the
user agent matches, the legacy `frontend_es5` one otherwise - and the
companion apps (iOS/Android) still fall into the legacy branch. On the legacy
path the `webcomponents` polyfill replaces `customElements` *after* the
document has started parsing.

`add_extra_js_url` injects an `import(...)` into index.html, i.e. it runs
during bootstrap, and it may therefore evaluate the card into the registry the
polyfill is about to discard. Modules are cached per URL, so the import the
Lovelace UI performs later is a no-op and the element never lands in the
registry the UI reads - the app then reports
"Custom element doesn't exist: singbox-panel-card". Which branch wins the race
depends on network timing, which is why the card appeared on desktop and
intermittently in the apps.

A Lovelace resource is imported by the frontend after it has booted, so it
always runs against the live registry. `add_extra_js_url` is only used as a
fallback, when no resource can be written (for example dashboards in YAML
mode).

Registration is best-effort: a Home Assistant instance without the frontend or
lovelace component (or a bare test harness) must still be able to set up the
integration, so every failure here is logged and swallowed.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__package__)

CARD_FILENAME = "singbox-panel-card.js"
CARD_URL_PATH = "/singbox-panel-card/singbox-panel-card.js"
DATA_CARD_REGISTERED = "singbox_card_registered"


def card_path() -> Path:
    """Absolute path of the bundled card."""
    return Path(__file__).with_name("www") / CARD_FILENAME


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the bundled card and make every dashboard load it."""
    path = card_path()
    if not path.is_file():
        _LOGGER.warning("Bundled panel card not found at %s", path)
        return

    try:
        from homeassistant.components.frontend import add_extra_js_url
        from homeassistant.components.http import StaticPathConfig
    except ImportError:  # pragma: no cover - frontend not installed
        _LOGGER.debug("Frontend components unavailable, not registering the card")
        return

    if getattr(hass, "http", None) is None:  # pragma: no cover - no http setup
        _LOGGER.debug("HTTP component unavailable, not registering the card")
        return

    # The static route can only be registered once per process.
    if not hass.data.get(DATA_CARD_REGISTERED):
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_URL_PATH, str(path), cache_headers=False)]
            )
            hass.data[DATA_CARD_REGISTERED] = True
        except Exception:  # noqa: BLE001 - never break setup over the card
            _LOGGER.exception("Could not register the bundled panel card")
            return

    if await _async_register_lovelace_resource(hass):
        return

    # No place to store a resource (YAML mode, lovelace not loaded, ...):
    # fall back to the extra frontend module. It is unreliable on the legacy
    # build, but it is better than not loading the card at all.
    try:
        add_extra_js_url(hass, CARD_URL_PATH)
    except Exception:  # noqa: BLE001 - never break setup over the card
        _LOGGER.exception("Could not load the bundled panel card")


async def _async_register_lovelace_resource(hass: HomeAssistant) -> bool:
    """Register the card as a Lovelace resource.

    Returns True when the resource is present, so the caller can skip the
    extra-module fallback.
    """
    try:
        from homeassistant.components.lovelace.const import (
            CONF_RESOURCE_TYPE_WS,
            LOVELACE_DATA,
        )
        from homeassistant.const import CONF_URL
    except ImportError:  # pragma: no cover - lovelace not installed
        return False

    lovelace_data: Any = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace_data, "resources", None)
    # YAML mode exposes a read-only collection: never touch it.
    if resources is None or not hasattr(resources, "async_create_item"):
        return False

    try:
        if not getattr(resources, "loaded", False):
            await resources.async_load()
            resources.loaded = True
        if any(item.get(CONF_URL) == CARD_URL_PATH for item in resources.async_items()):
            return True
        await resources.async_create_item(
            {CONF_RESOURCE_TYPE_WS: "module", CONF_URL: CARD_URL_PATH}
        )
        _LOGGER.debug("Registered the Sing-box Panel Card as a Lovelace resource")
        return True
    except Exception:  # noqa: BLE001 - never break setup over the card
        _LOGGER.exception("Could not register the panel card Lovelace resource")
        return False


async def async_unregister_card(hass: HomeAssistant) -> None:
    """Remove the Lovelace resource (used when the integration is removed)."""
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA
        from homeassistant.const import CONF_URL
    except ImportError:  # pragma: no cover - lovelace not installed
        return

    lovelace_data: Any = hass.data.get(LOVELACE_DATA)
    resources = getattr(lovelace_data, "resources", None)
    if resources is None or not hasattr(resources, "async_delete_item"):
        return

    try:
        if not getattr(resources, "loaded", False):
            await resources.async_load()
            resources.loaded = True
        for item in resources.async_items():
            if item.get(CONF_URL) == CARD_URL_PATH:
                await resources.async_delete_item(item["id"])
    except Exception:  # noqa: BLE001 - never break unload
        _LOGGER.exception("Could not remove the panel card Lovelace resource")
