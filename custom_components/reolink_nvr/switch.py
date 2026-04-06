"""Switch platform for Reolink NVR (PTZ patrol, IR lights)."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ReolinkNvrCoordinator
from .entity import ReolinkNvrEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ReolinkSwitchDescription(SwitchEntityDescription):
    """Describe a Reolink switch entity."""

    requires_ptz: bool = False


SWITCH_TYPES: tuple[ReolinkSwitchDescription, ...] = (
    ReolinkSwitchDescription(
        key="ptz_patrol",
        translation_key="ptz_patrol",
        icon="mdi:rotate-360",
        requires_ptz=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink NVR switches."""
    coordinator: ReolinkNvrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ReolinkSwitch] = []
    if coordinator.data:
        for channel, channel_data in coordinator.data.items():
            for description in SWITCH_TYPES:
                if description.requires_ptz and not channel_data.get("ptz_supported"):
                    continue
                entities.append(ReolinkSwitch(coordinator, channel, description))

    async_add_entities(entities)


class ReolinkSwitch(ReolinkNvrEntity, SwitchEntity):
    """Representation of a Reolink switch."""

    entity_description: ReolinkSwitchDescription

    def __init__(
        self,
        coordinator: ReolinkNvrCoordinator,
        channel: int,
        description: ReolinkSwitchDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, channel)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.nvr_serial}_{channel}_{description.key}"
        self._is_on = False

    @property
    def is_on(self) -> bool:
        """Return True if the switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the switch."""
        try:
            if self.entity_description.key == "ptz_patrol":
                await self.coordinator.api.set_ptz_command(self._channel, "StartPatrol")
        except Exception:
            _LOGGER.error(
                "Error turning on %s for channel %d",
                self.entity_description.key,
                self._channel,
                exc_info=True,
            )
            return

        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the switch."""
        try:
            if self.entity_description.key == "ptz_patrol":
                await self.coordinator.api.set_ptz_command(self._channel, "StopPatrol")
        except Exception:
            _LOGGER.error(
                "Error turning off %s for channel %d",
                self.entity_description.key,
                self._channel,
                exc_info=True,
            )
            return

        self._is_on = False
        self.async_write_ha_state()
