"""Number platform for Reolink NVR integration (PTZ speed, speaker volume)."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_PTZ_SPEED, DOMAIN
from .coordinator import ReolinkNvrCoordinator
from .entity import ReolinkNvrEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ReolinkNumberDescription(NumberEntityDescription):
    """Describe a Reolink number entity."""

    requires_ptz: bool = False
    requires_speaker: bool = False


NUMBER_TYPES: tuple[ReolinkNumberDescription, ...] = (
    ReolinkNumberDescription(
        key="ptz_speed",
        translation_key="ptz_speed",
        icon="mdi:speedometer",
        native_min_value=1,
        native_max_value=64,
        native_step=1,
        mode=NumberMode.SLIDER,
        requires_ptz=True,
    ),
    ReolinkNumberDescription(
        key="volume",
        translation_key="volume",
        icon="mdi:volume-high",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        requires_speaker=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink NVR number entities."""
    coordinator: ReolinkNvrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ReolinkNumber] = []
    if coordinator.data:
        for channel, channel_data in coordinator.data.items():
            for description in NUMBER_TYPES:
                if description.requires_ptz and not channel_data.get("ptz_supported"):
                    continue
                if description.requires_speaker and not channel_data.get("has_speaker"):
                    continue
                entities.append(ReolinkNumber(coordinator, channel, description))

    async_add_entities(entities)


class ReolinkNumber(ReolinkNvrEntity, NumberEntity):
    """Representation of a Reolink number entity."""

    entity_description: ReolinkNumberDescription

    def __init__(
        self,
        coordinator: ReolinkNvrCoordinator,
        channel: int,
        description: ReolinkNumberDescription,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, channel)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.nvr_serial}_{channel}_{description.key}"
        )
        self._value: float = (
            DEFAULT_PTZ_SPEED if description.key == "ptz_speed" else 50
        )

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self._value

    async def async_set_native_value(self, value: float) -> None:
        """Update the value."""
        self._value = value

        if self.entity_description.key == "volume":
            try:
                await self.coordinator.host.set_volume(
                    self._channel, volume=int(value)
                )
            except Exception:
                _LOGGER.error(
                    "Error setting volume for channel %d",
                    self._channel,
                    exc_info=True,
                )
        elif self.entity_description.key == "ptz_speed":
            # PTZ speed is stored locally — used by PTZ button commands
            pass

        self.async_write_ha_state()
