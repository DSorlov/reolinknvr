"""Constants for the Reolink NVR integration."""

from __future__ import annotations

DOMAIN = "reolink_nvr"

# Platforms to set up
PLATFORMS = [
    "binary_sensor",
    "button",
    "camera",
    "number",
    "select",
    "switch",
]

# Config keys
CONF_USE_HTTPS = "use_https"

# Default values
DEFAULT_PORT = 443
DEFAULT_TIMEOUT = 60
DEFAULT_PROTOCOL = "rtsp"
DEFAULT_STREAM = "sub"

# Streaming
STREAM_MAIN = "main"
STREAM_SUB = "sub"
STREAM_OPTIONS = [STREAM_SUB, STREAM_MAIN]

# Event names
EVENT_REOLINK_NVR = "reolink_nvr_event"

# Event types
EVENT_MOTION = "motion"
EVENT_PERSON = "person"
EVENT_VEHICLE = "vehicle"
EVENT_PET = "pet"
EVENT_DOORBELL = "doorbell"
EVENT_HDD_ERROR = "hdd_error"

# PTZ commands
PTZ_LEFT = "Left"
PTZ_RIGHT = "Right"
PTZ_UP = "Up"
PTZ_DOWN = "Down"
PTZ_ZOOM_IN = "ZoomInc"
PTZ_ZOOM_OUT = "ZoomDec"
PTZ_FOCUS_NEAR = "FocusInc"
PTZ_FOCUS_FAR = "FocusDec"
PTZ_STOP = "Stop"

PTZ_COMMANDS = {
    "left": PTZ_LEFT,
    "right": PTZ_RIGHT,
    "up": PTZ_UP,
    "down": PTZ_DOWN,
    "zoom_in": PTZ_ZOOM_IN,
    "zoom_out": PTZ_ZOOM_OUT,
    "focus_near": PTZ_FOCUS_NEAR,
    "focus_far": PTZ_FOCUS_FAR,
    "stop": PTZ_STOP,
}

# Defaults for options
DEFAULT_POLL_INTERVAL = 60
DEFAULT_PTZ_SPEED = 25

# Password constraints
MAX_PASSWORD_LENGTH = 31
