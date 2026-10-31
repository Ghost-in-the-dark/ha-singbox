"""Serve and register the bundled Sing-box Panel Card.

A card that depends 1:1 on an integration should ship inside it instead of
living in a separate repository. The bundled file is registered as an extra
frontend module, so `custom:singbox-panel-card` works right after the
integration is set up - no manual Lovelace resource entry needed.

Registration is best-effort: a Home Assistant instance without the frontend
component (or a bare test harness) must still be able to set up the
integration, so every failure here is logged and swallowed.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__package__)

CARD_FILENAME = "singbox-panel-card.js"
CARD_URL_PATH = "/singbox-panel-card/singbox-panel-card.js"
DATA_CARD_REGISTERED = "singbox_card_registered"


def card_path() -> Path:
    """Absolute path of the bundled card."""
    return Path(__file__).with_name("www") / CARD_FILENAME


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the bundled card and load it on every dashboard."""
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

    # The static route can only be registered once per process; the URL is
    # added back to the frontend on every setup so a reload still loads it.
    if not hass.data.get(DATA_CARD_REGISTERED):
        try:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(CARD_URL_PATH, str(path), cache_headers=False)]
            )
            hass.data[DATA_CARD_REGISTERED] = True
        except Exception:  # noqa: BLE001 - never break setup over the card
            _LOGGER.exception("Could not register the bundled panel card")
            return

    try:
        add_extra_js_url(hass, CARD_URL_PATH)
    except Exception:  # noqa: BLE001 - never break setup over the card
        _LOGGER.exception("Could not load the bundled panel card")


def async_unregister_card(hass: HomeAssistant) -> None:
    """Stop loading the card (the static route stays for the process lifetime)."""
    try:
        from homeassistant.components.frontend import remove_extra_js_url
    except ImportError:  # pragma: no cover - frontend not installed
        return
    try:
        remove_extra_js_url(hass, CARD_URL_PATH)
    except Exception:  # noqa: BLE001 - unload must not fail
        _LOGGER.exception("Could not unregister the bundled panel card")
