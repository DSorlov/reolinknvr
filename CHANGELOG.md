# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.5] - 2026-04-06

### Fixed

- PTZ detection now uses `GetAbility` per-channel abilities (single API call, read-only) instead of `GetPtzPreset` which returned 64 empty slots for all channels regardless of PTZ support.
- Binary sensors no longer all show as "Beläggning" (Swedish for occupancy). Removed `BinarySensorDeviceClass.OCCUPANCY` so translation keys ("Person", "Vehicle", "Pet", "Doorbell") are used as entity names.
- Person, vehicle, pet, and doorbell binary sensors are now only created for channels that support the respective detection type instead of being created for every channel.

### Added

- Doorbell camera detection via `GetAbility` (`supportDoorbellLight`). Doorbell channels get a dedicated ring binary sensor that checks the `visitor` alarm state in `GetAiState`.
- Visual config editors for all three custom Lovelace cards (camera card, camera grid card, PTZ feature). Cards can now be fully configured from the HA graphical dashboard editor.

### Removed

- IR lights switch entity — the NVR manages night mode automatically and the switch did not reliably reflect or control the state.

## [1.1.4] - 2026-04-06

### Changed

- Integration startup is now near-instant on subsequent loads. NVR and channel data is cached to disk via `homeassistant.helpers.storage.Store`. On restart, entities are created from cache immediately while a full NVR rediscovery runs in the background.

### Fixed

- Custom cards now wait for `ha-panel-lovelace` to be defined before initializing. Scripts loaded via `add_extra_js_url` execute before the Lovelace panel exists, causing `customElements.get()` to return `undefined` and silently crashing all three card files.

## [1.1.3] - 2026-04-06

### Fixed

- Custom Lovelace cards now auto-register with the frontend using `add_extra_js_url`. Previously, cards were served but never injected into the page.
- Changed card URL prefix from `/hacsfiles/reolink_nvr/` to `/reolink_nvr/` (served directly by the integration).
- PTZ detection no longer physically moves cameras during setup. Replaced `PtzCheck` (sends motor command) with read-only `GetPtzPreset` check — cameras with enabled presets are detected as PTZ-capable.

## [1.1.1] - 2026-04-06

### Fixed

- Use `async_register_static_paths` instead of removed `register_static_path` (HA 2025.x+ compatibility).
- Move SSL context creation off the event loop to avoid blocking call detection (`load_default_certs`, `set_default_verify_paths`).

## [1.1.0] - 2026-04-06

### Changed

- Replaced reolink-aio library with a direct NVR HTTP API client — fixes connection failures on RLN36 firmware v3.6.x.
- Default connection changed to HTTPS port 443 (matches NVR default).
- RTSP URLs now fetched from the NVR via `GetRtspUrl` instead of being constructed (fixes incorrect `h264Preview` path).
- Two-phase channel discovery: essentials (AI, RTSP) first, extras (audio, IR, PTZ) lazily to avoid overwhelming the NVR.
- Removed `reolink-aio` pip dependency — zero external requirements (uses HA's bundled aiohttp).
- SSL certificate verification disabled for self-signed NVR certs.

### Fixed

- NVR connection hanging due to unsupported `GetAbility` command on newer firmware.
- HTTPS self-signed certificate causing timeouts.
- Wrong RTSP stream URL format (`h264Preview_XX` → `Preview_XX`).

## [1.0.0] - 2026-04-06

### Added

- Initial release of the Reolink NVR integration for Home Assistant.
- **Camera streaming** — WebRTC via go2rtc with sub-stream default (~512 kbps). Switch to main stream via select entity.
- **Two-way audio** — Microphone button in custom camera card for intercom via go2rtc RTSP backchannel.
- **NVR event triggers** — Motion, person, vehicle, pet, doorbell, and HDD error events fired on the HA event bus (`reolink_nvr_event`). Real-time via Baichuan TCP push with polling fallback.
- **PTZ controls** — Directional buttons (left, right, up, down), zoom in/out, stop, preset selection, patrol toggle, and speed control.
- **Binary sensors** — Per-channel motion, person, vehicle, pet, and doorbell detection.
- **Speaker volume** — Number entity for camera speaker volume (0–100).
- **IR lights** — Switch entity to toggle infrared LEDs per channel.
- **Stream quality select** — Per-channel select entity to switch between sub-stream and main-stream.
- **Config flow** — UI-based setup with host, port, username, password, and HTTPS toggle. Password length validation (max 31 chars). Reauth flow for expired credentials.
- **Options flow** — Configurable default stream quality and polling interval.
- **Custom Lovelace cards**:
  - `reolink-camera-card` — Single camera view with WebRTC video, PTZ overlay, microphone button, pinch-to-zoom, double-tap fullscreen, and motion indicator.
  - `reolink-camera-grid-card` — Multi-camera NVR grid with auto-discovery, responsive columns, tap-to-expand.
  - `reolink-ptz-feature` — Compact PTZ card feature for tile and entity cards.
- **Multi-NVR support** — Each NVR is a separate config entry with its own coordinator.
- **HACS distribution** — Installable as a custom repository via HACS.

### Supported Models

- Reolink RLN36 (tested)
- Reolink RLN16 (expected)
- Reolink RLN8 (expected)
- Any Reolink NVR with HTTP JSON API support

[1.1.5]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.5
[1.1.4]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.4
[1.1.3]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.3
[1.1.1]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.1
[1.1.0]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.0
[1.0.0]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.0.0
