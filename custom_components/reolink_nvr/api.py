"""Direct Reolink NVR API client.

Lightweight async client that talks directly to the Reolink HTTP JSON API.
Replaces reolink-aio which doesn't work with newer NVR firmware (GetAbility
not supported, HTTPS self-signed cert issues).
"""

from __future__ import annotations

import logging
import ssl
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

# Timeout for individual API calls (seconds)
API_TIMEOUT = 8


class ReolinkNvrApiError(Exception):
    """General API error."""


class ReolinkAuthError(ReolinkNvrApiError):
    """Authentication error."""


class ReolinkConnectionError(ReolinkNvrApiError):
    """Connection error."""


class ReolinkNvrApi:
    """Async client for a Reolink NVR's HTTP JSON API."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 443,
        use_https: bool = True,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._username = username
        self._password = password
        self._port = port
        self._use_https = use_https
        self._token: str | None = None
        self._session: aiohttp.ClientSession | None = None

        # NVR info (populated after login)
        self.nvr_name: str = ""
        self.model: str = ""
        self.serial: str = ""
        self.mac_address: str = ""
        self.sw_version: str = ""
        self.hardware_version: str = ""
        self.num_channels: int = 0

        # Per-channel info (populated after get_host_data)
        self.channels: dict[int, ChannelInfo] = {}

        # Network info
        self.rtsp_port: int = 554

    @property
    def _base_url(self) -> str:
        scheme = "https" if self._use_https else "http"
        return f"{scheme}://{self._host}:{self._port}"

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session with SSL disabled for self-signed certs."""
        if self._session is None or self._session.closed:
            # Use SSLContext directly to avoid blocking calls from
            # ssl.create_default_context() (load_default_certs, set_default_verify_paths)
            ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
            self._session = aiohttp.ClientSession(
                connector=connector, timeout=timeout
            )
        return self._session

    async def _api_call(
        self, cmd: str, param: dict[str, Any] | None = None, action: int = 0
    ) -> list[dict[str, Any]]:
        """Make a single API call to the NVR."""
        session = await self._ensure_session()
        url = f"{self._base_url}/cgi-bin/api.cgi?cmd={cmd}"
        if self._token:
            url += f"&token={self._token}"

        body = [{"cmd": cmd, "action": action, "param": param or {}}]

        try:
            async with session.post(url, json=body) as resp:
                text = await resp.text()
                import json as json_mod

                return json_mod.loads(text)
        except aiohttp.ClientError as err:
            raise ReolinkConnectionError(
                f"Connection error to {self._host}: {err}"
            ) from err
        except Exception as err:
            raise ReolinkNvrApiError(
                f"API error for {cmd} on {self._host}: {err}"
            ) from err

    async def login(self) -> None:
        """Authenticate with the NVR and get a session token."""
        result = await self._api_call(
            "Login",
            {"User": {"userName": self._username, "password": self._password}},
        )

        resp = result[0]
        if resp.get("code") != 0:
            error = resp.get("error", {})
            detail = error.get("detail", "unknown")
            raise ReolinkAuthError(
                f"Login failed for {self._host}: {detail}"
            )

        self._token = resp["value"]["Token"]["name"]

    async def logout(self) -> None:
        """Log out and close the session."""
        if self._token:
            try:
                await self._api_call("Logout")
            except Exception:
                _LOGGER.debug("Error during logout", exc_info=True)
            self._token = None

        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_host_data(self) -> None:
        """Login and fetch NVR info + channel status + network config."""
        await self.login()

        # Device info
        result = await self._api_call("GetDevInfo")
        dev = result[0]["value"]["DevInfo"]
        self.nvr_name = dev.get("name", "NVR")
        self.model = dev.get("model", "Unknown")
        self.serial = dev.get("serial", dev.get("detail", ""))
        self.sw_version = dev.get("firmVer", "")
        self.hardware_version = dev.get("hardVer", "")
        self.num_channels = dev.get("channelNum", 0)

        # Network info (MAC + RTSP port)
        try:
            result = await self._api_call("GetLocalLink")
            link = result[0]["value"]["LocalLink"]
            self.mac_address = link.get("mac", "")
        except Exception:
            _LOGGER.debug("Could not get MAC address", exc_info=True)

        try:
            result = await self._api_call("GetNetPort")
            ports = result[0]["value"]["NetPort"]
            self.rtsp_port = ports.get("rtspPort", 554)
        except Exception:
            _LOGGER.debug("Could not get network ports", exc_info=True)

        # Channel status
        await self._refresh_channels()

    async def _refresh_channels(self) -> None:
        """Fetch channel status and discover capabilities for online channels."""
        result = await self._api_call("GetChannelstatus")
        statuses = result[0]["value"]["status"]

        for ch_status in statuses:
            ch = ch_status["channel"]
            online = ch_status.get("online", 0) == 1
            name = ch_status.get("name", f"Channel {ch}")

            if ch not in self.channels:
                self.channels[ch] = ChannelInfo(channel=ch, name=name, online=online)
            else:
                self.channels[ch].name = name
                self.channels[ch].online = online

        # Discover capabilities for online channels (essential data only)
        online_channels = [ch for ch, info in self.channels.items() if info.online]
        for ch in online_channels:
            await self._discover_channel_essentials(ch)

    async def _discover_channel_essentials(self, channel: int) -> None:
        """Discover essential capabilities: AI detection + RTSP URLs.

        Runs during initial setup. Keeps it fast by only fetching what's
        needed for entity creation.
        """
        ch_info = self.channels[channel]

        # AI detection capabilities
        try:
            result = await self._api_call("GetAiState", {"channel": channel})
            ai_val = result[0].get("value", {})
            ch_info.ai_people = isinstance(ai_val.get("people"), dict) and ai_val["people"].get("support", 0) == 1
            ch_info.ai_vehicle = isinstance(ai_val.get("vehicle"), dict) and ai_val["vehicle"].get("support", 0) == 1
            ch_info.ai_pet = isinstance(ai_val.get("dog_cat"), dict) and ai_val["dog_cat"].get("support", 0) == 1
        except Exception:
            _LOGGER.debug("Could not get AI state for ch %d", channel)

        # RTSP URLs
        try:
            result = await self._api_call("GetRtspUrl", {"channel": channel})
            urls = result[0]["value"]["rtspUrl"]
            ch_info.rtsp_main = urls.get("mainStream", "")
            ch_info.rtsp_sub = urls.get("subStream", "")
        except Exception:
            _LOGGER.debug("Could not get RTSP URLs for ch %d", channel)

    async def discover_channel_extras(self, channel: int) -> None:
        """Discover optional capabilities: audio, IR, PTZ.

        Called lazily after initial setup to avoid overwhelming the NVR.
        """
        ch_info = self.channels.get(channel)
        if ch_info is None or ch_info._extras_discovered:
            return

        # Audio
        try:
            result = await self._api_call("GetAudioCfg", {"channel": channel})
            ch_info.has_speaker = result[0].get("code") == 0
            if ch_info.has_speaker:
                ch_info.volume = result[0]["value"]["AudioCfg"].get("volume", 100)
        except Exception:
            _LOGGER.debug("Could not get audio config for ch %d", channel)

        # IR lights
        try:
            result = await self._api_call("GetIrLights", {"channel": channel})
            if result[0].get("code") == 0:
                ch_info.has_ir = True
                ch_info.ir_state = result[0]["value"]["IrLights"].get("state", "Auto")
        except Exception:
            _LOGGER.debug("Could not get IR state for ch %d", channel)

        # PTZ — detect by checking presets (read-only, doesn't move the camera)
        # PtzCheck physically moves the motor so we must NOT use it.
        try:
            result = await self._api_call("GetPtzPreset", {"channel": channel})
            presets = result[0].get("value", {}).get("PtzPreset", [])
            enabled = {
                p["id"]: p["name"]
                for p in presets
                if p.get("enable", 0) == 1 and p.get("name")
            }
            if enabled:
                ch_info.ptz_supported = True
                ch_info.ptz_presets = enabled
        except Exception:
            _LOGGER.debug("Could not check PTZ presets for ch %d", channel)

        ch_info._extras_discovered = True

    # --- State polling ---

    async def get_states(self) -> dict[int, dict[str, Any]]:
        """Poll current detection states for all online channels."""
        states: dict[int, dict[str, Any]] = {}

        # Refresh channel online status
        try:
            result = await self._api_call("GetChannelstatus")
            for ch_status in result[0]["value"]["status"]:
                ch = ch_status["channel"]
                if ch in self.channels:
                    self.channels[ch].online = ch_status.get("online", 0) == 1
                    self.channels[ch].name = ch_status.get("name", self.channels[ch].name)
        except Exception:
            _LOGGER.debug("Error refreshing channel status", exc_info=True)

        for ch, ch_info in self.channels.items():
            if not ch_info.online:
                continue

            state: dict[str, Any] = {
                "online": True,
                "name": ch_info.name,
                "motion": False,
                "person": False,
                "vehicle": False,
                "pet": False,
                "doorbell": False,
                "ptz_supported": ch_info.ptz_supported,
                "has_speaker": ch_info.has_speaker,
            }

            # Motion detection
            try:
                result = await self._api_call("GetMdState", {"channel": ch})
                state["motion"] = result[0]["value"].get("state", 0) == 1
            except Exception:
                pass

            # AI detection
            try:
                result = await self._api_call("GetAiState", {"channel": ch})
                ai = result[0].get("value", {})
                if ch_info.ai_people and isinstance(ai.get("people"), dict):
                    state["person"] = ai["people"].get("alarm_state", 0) == 1
                if ch_info.ai_vehicle and isinstance(ai.get("vehicle"), dict):
                    state["vehicle"] = ai["vehicle"].get("alarm_state", 0) == 1
                if ch_info.ai_pet and isinstance(ai.get("dog_cat"), dict):
                    state["pet"] = ai["dog_cat"].get("alarm_state", 0) == 1
            except Exception:
                pass

            states[ch] = state

        return states

    # --- Commands ---

    async def set_ptz_command(
        self, channel: int, command: str, speed: int = 25, preset: int | None = None
    ) -> None:
        """Send a PTZ command."""
        param: dict[str, Any] = {
            "channel": channel,
            "op": command,
            "speed": speed,
        }
        if preset is not None:
            param["id"] = preset

        await self._api_call("PtzCtrl", param)

    async def set_volume(self, channel: int, volume: int) -> None:
        """Set speaker volume for a channel."""
        await self._api_call(
            "SetAudioCfg",
            {"AudioCfg": {"channel": channel, "volume": volume}},
        )

    async def set_ir_lights(self, channel: int, state: str) -> None:
        """Set IR lights state ('Auto' or 'Off')."""
        await self._api_call(
            "SetIrLights",
            {"IrLights": {"channel": channel, "state": state}},
        )

    async def get_snapshot(self, channel: int) -> bytes | None:
        """Get a JPEG snapshot from a channel."""
        session = await self._ensure_session()
        url = (
            f"{self._base_url}/cgi-bin/api.cgi"
            f"?cmd=Snap&channel={channel}&rs=flushbuf"
        )
        if self._token:
            url += f"&token={self._token}"

        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception:
            _LOGGER.debug("Error getting snapshot for ch %d", channel, exc_info=True)
        return None


class ChannelInfo:
    """Holds discovered info and capabilities for a single NVR channel."""

    def __init__(self, channel: int, name: str, online: bool) -> None:
        """Initialize channel info."""
        self.channel = channel
        self.name = name
        self.online = online

        # RTSP URLs (from GetRtspUrl)
        self.rtsp_main: str = ""
        self.rtsp_sub: str = ""

        # AI detection support
        self.ai_people: bool = False
        self.ai_vehicle: bool = False
        self.ai_pet: bool = False

        # Audio
        self.has_speaker: bool = False
        self.volume: int = 100

        # PTZ
        self.ptz_supported: bool = False
        self.ptz_presets: dict[int, str] = {}

        # IR lights
        self.has_ir: bool = False
        self.ir_state: str = "Auto"

        # Whether extras (audio, IR, PTZ) have been discovered
        self._extras_discovered: bool = False
