"""DataUpdateCoordinator for Reolink NVR integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ReolinkAuthError, ReolinkConnectionError, ReolinkNvrApi, ReolinkNvrApiError
from .const import (
    CONF_USE_HTTPS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PORT,
    DOMAIN,
    EVENT_DOORBELL,
    EVENT_HDD_ERROR,
    EVENT_MOTION,
    EVENT_PERSON,
    EVENT_PET,
    EVENT_REOLINK_NVR,
    EVENT_VEHICLE,
)

_LOGGER = logging.getLogger(__name__)


class ReolinkNvrCoordinator(DataUpdateCoordinator[dict[int, dict[str, Any]]]):
    """Coordinator to manage data from a Reolink NVR."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        poll_interval = entry.options.get("poll_interval", DEFAULT_POLL_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_HOST]}",
            update_interval=timedelta(seconds=poll_interval),
        )

        use_https = entry.data.get(CONF_USE_HTTPS, True)
        port = entry.data.get(CONF_PORT, 443 if use_https else DEFAULT_PORT)

        self.api = ReolinkNvrApi(
            host=entry.data[CONF_HOST],
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            port=port,
            use_https=use_https,
        )

        self._previous_states: dict[int, dict[str, bool]] = {}

    @property
    def nvr_name(self) -> str:
        """Return the NVR display name."""
        return self.api.nvr_name or self.config_entry.data[CONF_HOST]

    @property
    def nvr_serial(self) -> str:
        """Return the NVR serial number."""
        return self.api.serial or self.api.mac_address or "unknown"

    @property
    def nvr_model(self) -> str:
        """Return the NVR model."""
        return self.api.model

    @property
    def nvr_sw_version(self) -> str:
        """Return the NVR firmware version."""
        return self.api.sw_version

    async def async_setup(self) -> None:
        """Set up the coordinator: login and fetch NVR data."""
        try:
            await self.api.get_host_data()
        except ReolinkAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Invalid credentials for {self.config_entry.data[CONF_HOST]}"
            ) from err
        except (ReolinkConnectionError, ReolinkNvrApiError) as err:
            raise UpdateFailed(
                f"Error connecting to {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err

    async def async_teardown(self) -> None:
        """Tear down the coordinator: logout."""
        try:
            await self.api.logout()
        except Exception:
            _LOGGER.debug("Error logging out from NVR", exc_info=True)

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch data from the NVR."""
        try:
            states = await self.api.get_states()
        except ReolinkAuthError as err:
            raise ConfigEntryAuthFailed(
                f"Invalid credentials for {self.config_entry.data[CONF_HOST]}"
            ) from err
        except (ReolinkConnectionError, ReolinkNvrApiError) as err:
            raise UpdateFailed(
                f"Error fetching data from {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err

        self._fire_events(states)
        return states

    def _fire_events(self, states: dict[int, dict[str, Any]]) -> None:
        """Fire HA events when detection states change to True."""
        event_keys = {
            "motion": EVENT_MOTION,
            "person": EVENT_PERSON,
            "vehicle": EVENT_VEHICLE,
            "pet": EVENT_PET,
            "doorbell": EVENT_DOORBELL,
        }

        for channel, channel_state in states.items():
            prev = self._previous_states.get(channel, {})

            for key, event_type in event_keys.items():
                current_val = channel_state.get(key, False)
                prev_val = prev.get(key, False)

                # Fire event on rising edge (False → True)
                if current_val and not prev_val:
                    self.hass.bus.async_fire(
                        EVENT_REOLINK_NVR,
                        {
                            "type": event_type,
                            "channel": channel,
                            "channel_name": channel_state.get("name", f"Channel {channel}"),
                            "nvr_name": self.nvr_name,
                            "nvr_serial": self.nvr_serial,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

            self._previous_states[channel] = {
                k: channel_state.get(k, False) for k in event_keys
            }
