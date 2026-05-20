"""Config flow for Ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    DurationSelector,
    DurationSelectorConfig,
)
from homeassistant.util import slugify

from .api import (
    OgeroApiClient,
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
    OgeroApiClientError,
    create_api_client,
)
from .const import (
    CONF_SCAN_INTERVAL,
    CONFIG_ENTRY_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .data import OgeroConfigEntry


def _username_unique_id(username: str) -> str:
    """Return a stable unique id for an Ogero login."""
    return cast("str", slugify(username))


def _seconds_to_duration_dict(total_seconds: int) -> dict[str, float]:
    """Build a DurationSelector-compatible dict from total seconds."""
    total_seconds = max(0, total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return {
        "days": 0.0,
        "hours": float(hours),
        "minutes": float(minutes),
        "seconds": float(seconds),
        "milliseconds": 0.0,
    }


def _clamp_scan_interval_seconds(seconds: int) -> int:
    """Clamp poll interval to integration limits."""
    lo = int(MIN_SCAN_INTERVAL.total_seconds())
    hi = int(MAX_SCAN_INTERVAL.total_seconds())
    return max(lo, min(seconds, hi))


class OgeroFlowHandler(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
    """Handle a config flow for Ogero."""

    VERSION = CONFIG_ENTRY_VERSION

    def __init__(self) -> None:
        """Initialize."""
        self._client: OgeroApiClient | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except OgeroApiClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except OgeroApiClientCommunicationError:
                errors["base"] = "cannot_connect"
            except OgeroApiClientError:
                LOGGER.exception("Unexpected error during credential test")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    _username_unique_id(user_input[CONF_USERNAME])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        _entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Confirm reauthentication."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()
        if user_input is not None:
            try:
                await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except OgeroApiClientAuthenticationError:
                errors["base"] = "invalid_auth"
            except OgeroApiClientCommunicationError:
                errors["base"] = "cannot_connect"
            except OgeroApiClientError:
                LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data=user_input,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or reauth_entry.data).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT,
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback  # type: ignore[untyped-decorator]
    def async_get_options_flow(
        _config_entry: OgeroConfigEntry,
    ) -> OgeroOptionsFlowHandler:
        """Get the options flow."""
        return OgeroOptionsFlowHandler()

    def _create_client(self, username: str, password: str) -> OgeroApiClient:
        if self._client is None:
            self._client = create_api_client(
                self.hass, username=username, password=password
            )
        return self._client

    async def _test_credentials(self, username: str, password: str) -> None:
        client = self._create_client(username, password)
        await client.async_login()


class OgeroOptionsFlowHandler(OptionsFlowWithReload):  # type: ignore[misc]
    """Handle Ogero options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            new_options = {**dict(self.config_entry.options)}
            if CONF_SCAN_INTERVAL in user_input and user_input[CONF_SCAN_INTERVAL] is not None:
                raw = user_input[CONF_SCAN_INTERVAL]
                interval_td = cv.positive_time_period_dict(raw)
                seconds = _clamp_scan_interval_seconds(int(interval_td.total_seconds()))
                new_options[CONF_SCAN_INTERVAL] = seconds
            return self.async_create_entry(data=new_options)

        default_seconds = _clamp_scan_interval_seconds(
            int(
                self.config_entry.options.get(
                    CONF_SCAN_INTERVAL,
                    int(DEFAULT_SCAN_INTERVAL.total_seconds()),
                )
            )
        )
        default_duration = _seconds_to_duration_dict(default_seconds)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=default_duration,
                    ): DurationSelector(
                        DurationSelectorConfig(
                            enable_day=False,
                            enable_millisecond=False,
                        ),
                    ),
                }
            ),
        )
