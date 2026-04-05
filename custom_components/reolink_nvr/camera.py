"""Camera platform for Reolink NVR integration."""

from __future__ import annotations

import logging
from urllib.parse import quote

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEFAULT_STREAM, DOMAIN, STREAM_MAIN, STREAM_SUB
from .coordinator import ReolinkNvrCoordinator
from .entity import ReolinkNvrEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Reolink NVR cameras."""
    coordinator: ReolinkNvrCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[ReolinkNvrCamera] = []
    if coordinator.data:
        for channel in coordinator.data:
            entities.append(ReolinkNvrCamera(coordinator, channel))

    async_add_entities(entities)


class ReolinkNvrCamera(ReolinkNvrEntity, Camera):
    """Representation of a Reolink NVR camera channel."""

    _attr_supported_features = (
        CameraEntityFeature.STREAM | CameraEntityFeature.ON_OFF
    )
    _attr_brand = "Reolink"

    def __init__(
        self,
        coordinator: ReolinkNvrCoordinator,
        channel: int,
    ) -> None:
        """Initialize the camera."""
        ReolinkNvrEntity.__init__(self, coordinator, channel)
        Camera.__init__(self)

        self._attr_unique_id = f"{coordinator.nvr_serial}_{channel}_camera"
        self._attr_translation_key = "camera"
        self._stream_quality: str = coordinator.config_entry.options.get(
            "stream_default", DEFAULT_STREAM
        )
        self._is_on = True

    @property
    def is_on(self) -> bool:
        """Return True if the camera is on."""
        return self._is_on

    @property
    def is_streaming(self) -> bool:
        """Return True if the camera is streaming."""
        return self._is_on

    @property
    def motion_detection_enabled(self) -> bool:
        """Return True if motion detection is enabled."""
        return True

    @property
    def extra_state_attributes(self) -> dict[str, str | bool]:
        """Return extra state attributes."""
        attrs: dict[str, str | bool] = {
            "channel": self._channel,
            "stream_quality": self._stream_quality,
        }
        data = self.coordinator.data
        if data and self._channel in data:
            attrs["has_speaker"] = data[self._channel].get("has_speaker", False)
            attrs["ptz_supported"] = data[self._channel].get("ptz_supported", False)
        return attrs

    async def stream_source(self) -> str | None:
        """Return the RTSP stream source URL.

        Sub-stream is used by default for low bandwidth.
        go2rtc (built into HA) auto-converts this to WebRTC for the frontend.
        """
        entry = self.coordinator.config_entry
        host = entry.data[CONF_HOST]
        port = entry.data.get(CONF_PORT, 80)
        username = entry.data[CONF_USERNAME]
        password = quote(entry.data[CONF_PASSWORD], safe="")

        # RTSP port is typically 554 regardless of HTTP port
        rtsp_port = 554

        stream_type = self._stream_quality
        return (
            f"rtsp://{username}:{password}@{host}:{rtsp_port}"
            f"/h264Preview_{self._channel + 1:02d}_{stream_type}"
        )

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image from the camera."""
        try:
            return await self.coordinator.host.get_snapshot(self._channel)
        except Exception:
            _LOGGER.debug(
                "Error getting snapshot for channel %d", self._channel, exc_info=True
            )
            return None

    async def async_turn_on(self) -> None:
        """Turn on the camera."""
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off the camera."""
        self._is_on = False
        self.async_write_ha_state()

    def set_stream_quality(self, quality: str) -> None:
        """Set the stream quality (sub or main)."""
        if quality in (STREAM_SUB, STREAM_MAIN):
            self._stream_quality = quality
            self.async_write_ha_state()
