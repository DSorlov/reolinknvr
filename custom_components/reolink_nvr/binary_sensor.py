"""Binary sensor platform for Reolink NVR integration."""

from __future__ import annotations

from dataclasses import dataclass

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
    capability_key: str | None = None


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
        state_key="person",
        capability_key="ai_people",
    ),
    ReolinkBinarySensorDescription(
        key="vehicle",
        translation_key="vehicle",
        state_key="vehicle",
        capability_key="ai_vehicle",
    ),
    ReolinkBinarySensorDescription(
        key="pet",
        translation_key="pet",
        state_key="pet",
        capability_key="ai_pet",
    ),
    ReolinkBinarySensorDescription(
        key="doorbell",
        translation_key="doorbell",
        state_key="doorbell",
        capability_key="is_doorbell",
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
            ch_info = coordinator.api.channels.get(channel)
            for description in BINARY_SENSOR_TYPES:
                # Only create sensor if camera supports this detection type
                if description.capability_key and ch_info:
                    if not getattr(ch_info, description.capability_key, False):
                        continue
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
        self._attr_unique_id = f"{coordinator.nvr_serial}_{channel}_{description.key}"

    @property
    def extra_state_attributes(self) -> dict[str, int]:
        """Expose the NVR channel index so frontend cards can match sensors."""
        return {"channel": self._channel}

    @property
    def is_on(self) -> bool | None:
        """Return True if the sensor detects something."""
        data = self.coordinator.data
        if data is None or self._channel not in data:
            return None
        return data[self._channel].get(self.entity_description.state_key, False)
