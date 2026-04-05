"""The Reolink NVR integration."""

from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN, PLATFORMS
from .coordinator import ReolinkNvrCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type ReolinkNvrConfigEntry = ConfigEntry


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Reolink NVR integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register frontend cards
    await _async_register_frontend(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Reolink NVR from a config entry."""
    coordinator = ReolinkNvrCoordinator(hass, entry)

    await coordinator.async_setup()
    await coordinator.async_config_entry_first_refresh()

    # Discover extra capabilities (audio, IR, PTZ) after initial entities are created
    # This is done lazily to avoid overwhelming the NVR during setup
    for channel in list(coordinator.api.channels):
        ch_info = coordinator.api.channels[channel]
        if ch_info.online:
            try:
                await coordinator.api.discover_channel_extras(channel)
            except Exception:
                _LOGGER.debug("Could not discover extras for ch %d", channel)

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Reolink NVR config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: ReolinkNvrCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_teardown()

    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register custom frontend cards."""
    www_dir = os.path.join(os.path.dirname(__file__), "www")
    if not os.path.isdir(www_dir):
        return

    card_files = [
        "reolink-camera-card.js",
        "reolink-camera-grid-card.js",
        "reolink-ptz-feature.js",
    ]

    for card_file in card_files:
        card_path = os.path.join(www_dir, card_file)
        if os.path.isfile(card_path):
            url_path = f"/hacsfiles/reolink_nvr/{card_file}"
            hass.http.register_static_path(
                url_path,
                card_path,
                cache_headers=True,
            )
            _LOGGER.debug("Registered frontend card: %s", url_path)

    # Register cards as Lovelace resources
    hass.data.setdefault("lovelace_resources", set())
    for card_file in card_files:
        resource_url = f"/hacsfiles/reolink_nvr/{card_file}"
        if resource_url not in hass.data["lovelace_resources"]:
            hass.data["lovelace_resources"].add(resource_url)
