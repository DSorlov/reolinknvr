"""The Reolink NVR integration."""

from __future__ import annotations

import logging
import os

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import ReolinkNvrCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type ReolinkNvrConfigEntry = ConfigEntry

SERVICE_PTZ_CONTROL = "ptz_control"
SERVICE_PTZ_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("command"): vol.In(
            [
                "left",
                "right",
                "up",
                "down",
                "zoom_in",
                "zoom_out",
                "focus_near",
                "focus_far",
                "stop",
            ]
        ),
        vol.Optional("speed", default=25): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=64)
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Reolink NVR integration."""
    hass.data.setdefault(DOMAIN, {})

    # Register frontend cards
    await _async_register_frontend(hass)

    # Register PTZ service once (shared across all config entries)
    if not hass.services.has_service(DOMAIN, SERVICE_PTZ_CONTROL):

        async def _handle_ptz_control(call: ServiceCall) -> None:
            """Handle ptz_control service call."""
            entity_id: str = call.data["entity_id"]
            command: str = call.data["command"]
            speed: int = call.data.get("speed", 25)

            # Find the coordinator + channel for this camera entity
            entity_reg = er.async_get(hass)
            entry = entity_reg.async_get(entity_id)
            if entry is None or entry.platform != DOMAIN:
                _LOGGER.error("Entity %s is not a %s camera", entity_id, DOMAIN)
                return

            # Extract channel from unique_id: {serial}_{channel}_camera
            try:
                channel = int(entry.unique_id.split("_")[-2])
            except (ValueError, IndexError):
                _LOGGER.error("Cannot parse channel from %s", entry.unique_id)
                return

            # Find the coordinator for this config entry
            coordinator: ReolinkNvrCoordinator | None = hass.data.get(DOMAIN, {}).get(
                entry.config_entry_id
            )
            if coordinator is None:
                _LOGGER.error("No coordinator for entry %s", entry.config_entry_id)
                return

            _LOGGER.debug(
                "PTZ %s ch %d cmd=%s speed=%d",
                coordinator.nvr_serial,
                channel,
                command,
                speed,
            )
            await coordinator.api.set_ptz_command(channel, command, speed)

        hass.services.async_register(
            DOMAIN, SERVICE_PTZ_CONTROL, _handle_ptz_control, schema=SERVICE_PTZ_SCHEMA
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a Reolink NVR from a config entry."""
    coordinator = ReolinkNvrCoordinator(hass, entry)

    await coordinator.async_setup()

    if coordinator._loaded_from_cache:
        # Cache hit — login for polling, then schedule full refresh in background
        try:
            await coordinator.api.login()
        except Exception:
            _LOGGER.warning("Login failed after cache load, will retry on next poll")

        await coordinator.async_config_entry_first_refresh()

        # Full NVR discovery runs in background so entities appear instantly
        entry.async_create_background_task(
            hass,
            coordinator.async_full_refresh(),
            f"{DOMAIN}_bg_refresh_{entry.entry_id}",
        )
    else:
        # No cache — first time setup, do everything synchronously
        await coordinator.async_config_entry_first_refresh()

        for channel in list(coordinator.api.channels):
            ch_info = coordinator.api.channels[channel]
            if ch_info.online:
                try:
                    await coordinator.api.discover_channel_extras(channel)
                except Exception:
                    _LOGGER.debug("Could not discover extras for ch %d", channel)

        await coordinator.async_save_cache()

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


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register custom frontend cards."""
    from homeassistant.components.frontend import add_extra_js_url
    from homeassistant.components.http import StaticPathConfig

    www_dir = os.path.join(os.path.dirname(__file__), "www")
    if not os.path.isdir(www_dir):
        return

    # Read version for cache-busting query parameter
    from .const import DOMAIN  # noqa: F811

    manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
    version = ""
    try:
        import json

        with open(manifest_path) as f:
            version = json.load(f).get("version", "")
    except Exception:
        pass

    card_files = [
        "reolink-camera-card.js",
        "reolink-camera-grid-card.js",
        "reolink-ptz-feature.js",
    ]

    paths_to_register: list[StaticPathConfig] = []
    for card_file in card_files:
        card_path = os.path.join(www_dir, card_file)
        if os.path.isfile(card_path):
            url_path = f"/reolink_nvr/{card_file}"
            paths_to_register.append(
                StaticPathConfig(url_path, card_path, cache_headers=False)
            )

    if paths_to_register:
        await hass.http.async_register_static_paths(paths_to_register)

    # Inject cards into the frontend with cache-busting version param
    for card_file in card_files:
        url_path = f"/reolink_nvr/{card_file}"
        if version:
            url_path += f"?v={version}"
        add_extra_js_url(hass, url_path)
        _LOGGER.debug("Registered frontend card: %s", url_path)
