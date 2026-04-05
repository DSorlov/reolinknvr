# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.2] - 2026-04-06

### Fixed

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

[1.1.2]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.2
[1.1.1]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.1
[1.1.0]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.1.0
[1.0.0]: https://github.com/dsorlov/reolinknvr/releases/tag/v1.0.0
