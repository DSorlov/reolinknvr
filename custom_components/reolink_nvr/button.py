"""Button platform for Reolink NVR PTZ controls."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    PTZ_DOWN,
    PTZ_FOCUS_FAR,
    PTZ_FOCUS_NEAR,
    PTZ_LEFT,
    PTZ_RIGHT,
    PTZ_STOP,
    PTZ_UP,
    PTZ_ZOOM_IN,
    PTZ_ZOOM_OUT,
)
from .coordinator import ReolinkNvrCoordinator
from .entity import ReolinkNvrEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class ReolinkPtzButtonDescription(ButtonEntityDescription):
    """Describe a Reolink PTZ button."""

    ptz_command: str


PTZ_BUTTON_TYPES: tuple[ReolinkPtzButtonDescription, ...] = (
    ReolinkPtzButtonDescription(
        key="ptz_left",
        translation_key="ptz_left",
        icon="mdi:pan-left",
        ptz_command=PTZ_LEFT,
    ),
    ReolinkPtzButtonDescription(
        key="ptz_right",
        translation_key="ptz_right",
        icon="mdi:pan-right",
        ptz_command=PTZ_RIGHT,
    ),
    ReolinkPtzButtonDescription(
        key="ptz_up",
        translation_key="ptz_up",
        icon="mdi:pan-up",
        ptz_command=PTZ_UP,
    ),
    ReolinkPtzButtonDescription(
        key="ptz_down",
        translation_key="ptz_down",
        icon="mdi:pan-down",
        ptz_command=PTZ_DOWN,
    ),
    ReolinkPtzButtonDescription(
        key="ptz_zoom_in",
        translation_key="ptz_zoom_in",
        icon="mdi:magnify-plus",
        ptz_command=PTZ_ZOOM_IN,
    ),
    ReolinkPtzButtonDescription(
        key="ptz_zoom_out",
        translation_key="ptz_zoom_out",
        icon="mdi:magnify-minus",
        ptz_command=PTZ_ZOOM_OUT,
    ),
    ReolinkPtzButtonDescription(
        key="ptz_stop",
        translation_key="ptz_stop",
        icon="mdi:stop",
        ptz_command=PTZ_STOP,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink NVR PTZ buttons."""
    coordinator: ReolinkNvrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ReolinkPtzButton] = []
    if coordinator.data:
        for channel, channel_data in coordinator.data.items():
            if channel_data.get("ptz_supported"):
                for description in PTZ_BUTTON_TYPES:
                    entities.append(
                        ReolinkPtzButton(coordinator, channel, description)
                    )

    async_add_entities(entities)


class ReolinkPtzButton(ReolinkNvrEntity, ButtonEntity):
    """Representation of a Reolink PTZ button."""

    entity_description: ReolinkPtzButtonDescription

    def __init__(
        self,
        coordinator: ReolinkNvrCoordinator,
        channel: int,
        description: ReolinkPtzButtonDescription,
    ) -> None:
        """Initialize the PTZ button."""
        super().__init__(coordinator, channel)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.nvr_serial}_{channel}_{description.key}"
        )

    async def async_press(self) -> None:
        """Handle the button press — send PTZ command."""
        try:
            await self.coordinator.api.set_ptz_command(
                self._channel, self.entity_description.ptz_command
            )
        except Exception:
            _LOGGER.error(
                "Error sending PTZ command %s to channel %d",
                self.entity_description.ptz_command,
                self._channel,
                exc_info=True,
            )
