"""Binary sensor platform for Reolink NVR integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ReolinkNvrCoordinator
from .entity import ReolinkNvrEntity


@dataclass(frozen=True, kw_only=True)
class ReolinkBinarySensorDescription(BinarySensorEntityDescription):
    """Describe a Reolink NVR binary sensor."""

    state_key: str
    detection_type: str | None = None


BINARY_SENSOR_TYPES: tuple[ReolinkBinarySensorDescription, ...] = (
    ReolinkBinarySensorDescription(
        key="motion",
        translation_key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
        state_key="motion",
    ),
    ReolinkBinarySensorDescription(
        key="person",
        translation_key="person",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        state_key="person",
    ),
    ReolinkBinarySensorDescription(
        key="vehicle",
        translation_key="vehicle",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        state_key="vehicle",
    ),
    ReolinkBinarySensorDescription(
        key="pet",
        translation_key="pet",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        state_key="pet",
    ),
    ReolinkBinarySensorDescription(
        key="doorbell",
        translation_key="doorbell",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
        state_key="doorbell",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink NVR binary sensors."""
    coordinator: ReolinkNvrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ReolinkNvrBinarySensor] = []
    if coordinator.data:
        for channel in coordinator.data:
            for description in BINARY_SENSOR_TYPES:
                entities.append(
                    ReolinkNvrBinarySensor(coordinator, channel, description)
                )

    async_add_entities(entities)


class ReolinkNvrBinarySensor(ReolinkNvrEntity, BinarySensorEntity):
    """Representation of a Reolink NVR binary sensor."""

    entity_description: ReolinkBinarySensorDescription

    def __init__(
        self,
        coordinator: ReolinkNvrCoordinator,
        channel: int,
        description: ReolinkBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, channel)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.nvr_serial}_{channel}_{description.key}"
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the sensor detects something."""
        data = self.coordinator.data
        if data is None or self._channel not in data:
            return None
        return data[self._channel].get(self.entity_description.state_key, False)
