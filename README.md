# Reolink NVR Integration for Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/dsorlov/reolinknvr)](https://github.com/dsorlov/reolinknvr/releases)
[![License](https://img.shields.io/github/license/dsorlov/reolinknvr)](LICENSE)

A lean, NVR-focused Home Assistant custom integration for **Reolink RLN36** and other NVRs in the same family (RLN8, RLN16, RLN36). Installed as a [HACS custom repository](https://hacs.xyz/docs/faq/custom_repositories/) — this integration is **not** part of the default HACS store.

## Features

- **WebRTC streaming** — Sub-stream by default (~512 kbps) for low bandwidth; switch to main stream on demand. Powered by Home Assistant's built-in go2rtc (zero-config WebRTC with ~0.5 s latency).
- **Two-way audio** — Microphone button in the custom camera card streams your voice to the camera speaker via go2rtc's RTSP backchannel (requires HA over HTTPS).
- **NVR events as HA triggers** — Motion, person, vehicle, pet, and doorbell detections fire `reolink_nvr_event` events. Use them in automations. State changes detected via polling.
- **PTZ controls** — Directional buttons, zoom, presets, patrol toggle, and speed control for PTZ-capable cameras.
- **Custom Lovelace cards** — Touch-friendly camera card with PTZ overlay and mic, NVR grid card, and a compact PTZ card feature for tile/entity cards.
- **Multi-NVR support** — Add as many Reolink NVRs as you need, each as a separate config entry.
- **Speaker volume control** — Adjust camera speaker volume for two-way audio.

## Supported Models

| NVR Model | Channels | Status |
|-----------|----------|--------|
| RLN36     | 36       | ✅ Tested |
| RLN16     | 16       | ✅ Expected to work |
| RLN8      | 8        | ✅ Expected to work |

Any Reolink NVR with an HTTP API (JSON over HTTPS) should work. This integration uses a custom direct HTTP API client — no third-party libraries required.

## Installation

### HACS (Recommended)

1. Open Home Assistant and go to **HACS** → **Integrations**.
2. Click the **⋮** menu (top right) and select **Custom repositories**.
3. Add the repository URL:
   ```
   https://github.com/dsorlov/reolinknvr
   ```
4. Set the category to **Integration** and click **Add**.
5. Search for **Reolink NVR** in HACS and click **Download**.
6. **Restart Home Assistant**.

### Manual Installation

1. Download the [latest release](https://github.com/dsorlov/reolinknvr/releases) and extract it.
2. Copy the `custom_components/reolink_nvr` folder into your Home Assistant `config/custom_components/` directory.
3. **Restart Home Assistant**.

## Configuration

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for **Reolink NVR**.
3. Enter your NVR connection details:
   - **Host**: IP address or hostname of the NVR
   - **Port**: HTTP/HTTPS port (default: 443)
   - **Username**: Admin username
   - **Password**: Password (max 31 characters — [Reolink firmware limitation](https://github.com/home-assistant/core/issues/139710))
   - **Use HTTPS**: Toggle if your NVR requires HTTPS (enabled by default)
4. Click **Submit**. The integration will connect, discover all camera channels, and create entities.

### Options

After setup, click **Configure** on the integration to adjust:

| Option | Default | Description |
|--------|---------|-------------|
| **Default stream quality** | `sub` | `sub` (low bandwidth ~512 kbps) or `main` (full quality) |
| **Polling interval** | 60 s | How often to poll NVR state |

## Entities Created

For each connected camera channel on the NVR:

| Platform | Entity | Description |
|----------|--------|-------------|
| `camera` | Camera stream | WebRTC live stream (sub or main) + still snapshots |
| `binary_sensor` | Motion | Motion detection state |
| `binary_sensor` | Person | AI person detection |
| `binary_sensor` | Vehicle | AI vehicle detection |
| `binary_sensor` | Pet | AI pet detection |
| `binary_sensor` | Doorbell | Doorbell press (if applicable) |
| `select` | Stream Quality | Switch between sub-stream and main-stream |
| `button` | PTZ Left/Right/Up/Down/Zoom In/Zoom Out/Stop | PTZ directional controls *(PTZ cameras only)* |
| `number` | PTZ Speed | PTZ movement speed 1–64 *(PTZ cameras only)* |
| `number` | Speaker Volume | Camera speaker volume 0–100 *(cameras with speaker only)* |
| `select` | PTZ Preset | Move to a saved PTZ preset position *(PTZ cameras only)* |
| `switch` | PTZ Patrol | Toggle automatic PTZ patrol *(PTZ cameras only)* |

## Custom Lovelace Cards

The integration bundles three custom Lovelace cards (auto-registered, no manual resource import needed):

### `reolink-camera-card` — Single Camera View

Full-featured camera card with WebRTC video, PTZ controls, and two-way audio.

```yaml
type: custom:reolink-camera-card
entity: camera.reolink_nvr_my_nvr_ch01_sub
ptz: true
show_motion_indicator: true
show_microphone: true
show_audio: true
show_header: true
show_fullscreen: true
```

**Touch gestures:**
- **Double-tap** → Fullscreen
- **Pinch** → Digital zoom
- **PTZ pad** → Hold to move continuously, release to stop
- **Mic button** → Tap to toggle two-way audio

### `reolink-camera-grid-card` — NVR Overview

Grid showing all NVR camera channels. Tap a cell to expand to the full camera card.

```yaml
type: custom:reolink-camera-grid-card
columns: 3
show_motion_indicator: true
allow_fullscreen: true
show_name: true
padding: 4
gap: 4
aspect_ratio: "16/9"
```

Set `columns: 0` for auto-sizing (2 on phone, 3–4 on tablet).

### `reolink-ptz-feature` — PTZ Card Feature

Compact PTZ controls that attach to tile or picture-entity cards.

```yaml
type: tile
entity: camera.reolink_nvr_my_nvr_ch01_sub
features:
  - type: custom:reolink-ptz-feature
    show_zoom: true
    show_presets: true
```

## Automation Events

The integration fires `reolink_nvr_event` on the HA event bus when detections occur:

```yaml
trigger:
  - platform: event
    event_type: reolink_nvr_event
    event_data:
      type: person
      channel_name: Front Door
```

**Event data:**

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | `motion`, `person`, `vehicle`, `pet`, `doorbell`, `hdd_error` |
| `channel` | int | Channel index (0-based) |
| `channel_name` | string | Camera name as configured on the NVR |
| `nvr_name` | string | NVR display name |
| `nvr_serial` | string | NVR serial number |
| `timestamp` | string | ISO 8601 UTC timestamp |

## Requirements

- **Home Assistant** 2024.11.0 or newer (go2rtc built-in)
- **HACS** installed for easy installation
- **Network**: NVR must be reachable from HA on ports 80/443 (HTTP/HTTPS) and 554 (RTSP)
- **HTTPS on HA** required for two-way audio (browser microphone needs secure context)
- **NVR password** must be 31 characters or fewer

## Troubleshooting

### Cannot connect to NVR

- Verify the NVR IP address and port (default 443 for HTTPS).
- Ensure HA can reach the NVR on ports 80/443 and 554.
- Try toggling the **Use HTTPS** option.

### Invalid authentication

- Check username and password.
- **Password must be 31 characters or fewer.** Longer passwords fail on both HTTP API and Baichuan protocol. Change it in the Reolink app/web UI.
- If you have non-Reolink ONVIF cameras on the NVR, they may cause auth issues. Try removing them.

### Stream not loading / high latency

- Ensure go2rtc is working (check **Settings** → **System** → **Repairs**).
- The default sub-stream uses H.264 which go2rtc passes through without transcoding.
- If using a reverse proxy, ensure WebSocket connections are allowed.

### Two-way audio not working

- Home Assistant **must be served over HTTPS** (browser requires secure context for microphone access).
- The camera must have a built-in speaker (`has_speaker` attribute on the camera entity).
- Check browser permissions for microphone access.

### PTZ not working

- Only PTZ-capable cameras show PTZ entities. Check `ptz_supported` attribute on the camera entity.
- Some cameras require specific firmware for full PTZ support.

## Coexistence with Official Integration

This integration uses the domain `reolink_nvr`, which does **not** conflict with the official `reolink` integration. You can run both simultaneously if needed, though configuring the same NVR in both is not recommended.

## Contributing

Contributions are welcome! Please open an issue or pull request on [GitHub](https://github.com/dsorlov/reolinknvr).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
