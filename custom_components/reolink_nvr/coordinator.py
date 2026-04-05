"""DataUpdateCoordinator for Reolink NVR integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from reolink_aio.api import Host
from reolink_aio.exceptions import (
    CredentialsInvalidError,
    LoginError,
    ReolinkConnectionError,
    ReolinkError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_USE_HTTPS,
    DEFAULT_POLL_INTERVAL,
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

        self.host = Host(
            entry.data[CONF_HOST],
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            port=entry.data.get(CONF_PORT, 80),
            use_https=entry.data.get(CONF_USE_HTTPS, False),
        )

        self._push_enabled = False
        self._previous_states: dict[int, dict[str, bool]] = {}

    @property
    def nvr_name(self) -> str:
        """Return the NVR display name."""
        return self.host.nvr_name or self.config_entry.data[CONF_HOST]

    @property
    def nvr_serial(self) -> str:
        """Return the NVR serial number."""
        return self.host.nvr_serial or self.host.mac_address or "unknown"

    async def async_setup(self) -> None:
        """Set up the coordinator: login and start push events."""
        try:
            await self.host.get_host_data()
        except CredentialsInvalidError as err:
            raise ConfigEntryAuthFailed(
                f"Invalid credentials for {self.config_entry.data[CONF_HOST]}"
            ) from err
        except (ReolinkConnectionError, ReolinkError) as err:
            raise UpdateFailed(
                f"Error connecting to {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err

        # Attempt to start Baichuan TCP push for real-time events
        await self._async_start_push()

    async def _async_start_push(self) -> None:
        """Try to subscribe to Baichuan TCP push events."""
        try:
            if not hasattr(self.host, "baichuan") or self.host.baichuan is None:
                _LOGGER.debug("Baichuan not available, using polling only")
                return

            self.host.baichuan.register_callback(
                "reolink_nvr_events", self._push_event_callback
            )
            await self.host.baichuan.subscribe_events()
            self._push_enabled = True
            _LOGGER.info(
                "Baichuan push events enabled for %s",
                self.config_entry.data[CONF_HOST],
            )
        except Exception:
            _LOGGER.debug(
                "Baichuan push not available for %s, falling back to polling",
                self.config_entry.data[CONF_HOST],
                exc_info=True,
            )

    @callback
    def _push_event_callback(self, event_data: Any) -> None:
        """Handle a push event from Baichuan."""
        self.async_set_updated_data(self._parse_states())

    async def async_teardown(self) -> None:
        """Tear down the coordinator: unsubscribe and logout."""
        if self._push_enabled:
            try:
                self.host.baichuan.unregister_callback("reolink_nvr_events")
            except Exception:
                _LOGGER.debug("Error unregistering Baichuan callback", exc_info=True)

        try:
            await self.host.logout()
        except Exception:
            _LOGGER.debug("Error logging out from NVR", exc_info=True)

    async def _async_update_data(self) -> dict[int, dict[str, Any]]:
        """Fetch data from the NVR."""
        try:
            await self.host.get_states()
        except CredentialsInvalidError as err:
            raise ConfigEntryAuthFailed(
                f"Invalid credentials for {self.config_entry.data[CONF_HOST]}"
            ) from err
        except LoginError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ReolinkConnectionError, ReolinkError) as err:
            raise UpdateFailed(
                f"Error fetching data from {self.config_entry.data[CONF_HOST]}: {err}"
            ) from err

        states = self._parse_states()
        self._fire_events(states)
        return states

    def _parse_states(self) -> dict[int, dict[str, Any]]:
        """Parse channel states from the host."""
        result: dict[int, dict[str, Any]] = {}

        for channel in range(self.host.num_channel):
            if not self.host.channel_online(channel):
                continue

            channel_state: dict[str, Any] = {
                "online": True,
                "name": self.host.camera_name(channel),
                "model": self.host.camera_model(channel),
                # Detection states
                "motion": self.host.motion_detected(channel),
                "person": self.host.ai_detected(channel, "people"),
                "vehicle": self.host.ai_detected(channel, "vehicle"),
                "pet": self.host.ai_detected(channel, "dog_cat"),
                # Capabilities
                "ptz_supported": self.host.ptz_supported(channel),
                "has_speaker": self._has_speaker(channel),
            }

            # Doorbell detection if supported
            try:
                channel_state["doorbell"] = self.host.doorbell_pressed(channel)
            except (AttributeError, TypeError):
                channel_state["doorbell"] = False

            result[channel] = channel_state

        return result

    def _has_speaker(self, channel: int) -> bool:
        """Check if a channel's camera has speaker support."""
        try:
            return self.host.audio_support(channel)
        except (AttributeError, TypeError):
            return False

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
