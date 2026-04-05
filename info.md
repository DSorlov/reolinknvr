# Reolink NVR Integration

A lean, NVR-focused Home Assistant integration for **Reolink RLN36** and family.

## Highlights

- **WebRTC streaming** with go2rtc — sub-stream by default for low bandwidth
- **Two-way audio** — talk to cameras from the HA dashboard
- **Real-time NVR events** — motion, person, vehicle, pet, doorbell as automation triggers
- **PTZ controls** — full directional, zoom, presets, and patrol
- **Custom touch-friendly cards** — camera card with PTZ overlay, NVR grid card, PTZ card feature

## Quick Start

1. Install via HACS (add as **custom repository**)
2. Restart Home Assistant
3. Add the integration: **Settings → Devices & Services → Add Integration → Reolink NVR**
4. Enter NVR IP, username, and password
5. All camera channels are auto-discovered

See the [README](https://github.com/dsorlov/reolinknvr) for full documentation.
