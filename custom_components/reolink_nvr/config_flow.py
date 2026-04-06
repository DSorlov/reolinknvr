"""Config flow for Reolink NVR integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback

from .api import (
    ReolinkAuthError,
    ReolinkConnectionError,
    ReolinkNvrApi,
    ReolinkNvrApiError,
)
from .const import (
    CONF_USE_HTTPS,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_STREAM,
    DOMAIN,
    MAX_PASSWORD_LENGTH,
    STREAM_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=443): int,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_USE_HTTPS, default=True): bool,
    }
)

REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


async def _test_connection(
    host: str,
    port: int,
    username: str,
    password: str,
    use_https: bool,
) -> tuple[str | None, dict[str, str]]:
    """Test connection to a Reolink NVR and return (unique_id, errors)."""
    errors: dict[str, str] = {}
    unique_id: str | None = None

    api = ReolinkNvrApi(
        host=host,
        username=username,
        password=password,
        port=port,
        use_https=use_https,
    )
    try:
        await api.get_host_data()
        unique_id = api.serial or api.mac_address
    except ReolinkAuthError:
        errors["base"] = "invalid_auth"
    except ReolinkConnectionError:
        errors["base"] = "cannot_connect"
    except ReolinkNvrApiError:
        errors["base"] = "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error connecting to Reolink NVR")
        errors["base"] = "unknown"
    finally:
        await api.logout()

    return unique_id, errors


class ReolinkNvrConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Reolink NVR."""

    VERSION = 1

    _host: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            password = user_input[CONF_PASSWORD]
            if len(password) > MAX_PASSWORD_LENGTH:
                errors["base"] = "password_too_long"
            else:
                unique_id, errors = await _test_connection(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                    username=user_input[CONF_USERNAME],
                    password=password,
                    use_https=user_input.get(CONF_USE_HTTPS, False),
                )

                if not errors and unique_id:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=user_input[CONF_HOST],
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=USER_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication."""
        self._host = entry_data[CONF_HOST]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-auth confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
            if entry is None:
                return self.async_abort(reason="unknown")

            password = user_input[CONF_PASSWORD]
            if len(password) > MAX_PASSWORD_LENGTH:
                errors["base"] = "password_too_long"
            else:
                _, errors = await _test_connection(
                    host=entry.data[CONF_HOST],
                    port=entry.data[CONF_PORT],
                    username=user_input[CONF_USERNAME],
                    password=password,
                    use_https=entry.data.get(CONF_USE_HTTPS, False),
                )

                if not errors:
                    self.hass.config_entries.async_update_entry(
                        entry,
                        data={**entry.data, **user_input},
                    )
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"host": self._host},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow handler."""
        return ReolinkNvrOptionsFlow(config_entry)


class ReolinkNvrOptionsFlow(OptionsFlow):
    """Handle options for Reolink NVR."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self._config_entry.options

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        "stream_default",
                        default=current.get("stream_default", DEFAULT_STREAM),
                    ): vol.In(STREAM_OPTIONS),
                    vol.Optional(
                        "poll_interval",
                        default=current.get("poll_interval", DEFAULT_POLL_INTERVAL),
                    ): vol.All(int, vol.Range(min=10, max=3600)),
                }
            ),
        )
