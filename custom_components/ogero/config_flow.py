"""Adds config flow for Ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    Account,
    OgeroApiClient,
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
    OgeroApiClientError,
)
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.config_entries import ConfigFlowResult

ACCOUNT = "account"
IS_NEW = "is_new"


@callback
def configured_instances(hass: HomeAssistant) -> set[str]:
    """Return a set of configured instances."""
    entries: list[Any] = [
        entry.data.get(ACCOUNT) for entry in hass.config_entries.async_entries(DOMAIN)
    ]
    return set(entries)


class OgeroFlowHandler(ConfigFlow, domain=DOMAIN):
    """Config flow for Ogero."""

    VERSION = 1

    _client: OgeroApiClient | None = None
    _user_data: dict

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except OgeroApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except OgeroApiClientCommunicationError as exception:
                LOGGER.error(exception)
                _errors["base"] = "connection"
            except OgeroApiClientError as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                self._user_data = user_input
                self._user_data[IS_NEW] = True
                return await self.async_step_account()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_account(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            is_predefined = user_input[ACCOUNT] in configured_instances(self.hass)

            if is_predefined:
                _errors[ACCOUNT] = "account_already_configured"

            if len(_errors) == 0:
                account = Account.deserialize(user_input[ACCOUNT])

                data = {**self._user_data, **user_input}
                del data[IS_NEW]
                if self._user_data[IS_NEW]:
                    return self.async_create_entry(
                        title=str(account),
                        data=data,
                    )

                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data=data
                )

        accounts = await self._get_accounts("", "")

        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(ACCOUNT): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=account.serial, label=str(account)
                                )
                                for account in accounts
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=False,
                            translation_key=ACCOUNT,
                        )
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauth on credential failure."""
        LOGGER.warning(f"async_step_reauth entry_data: {entry_data}")
        self._user_data = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle users reauth credentials."""
        errors: dict[str, str] | None = {}

        if user_input is not None:
            user_input[CONF_USERNAME] = self._user_data[CONF_USERNAME]
            try:
                await self._test_credentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
            except OgeroApiClientAuthenticationError as exception:
                LOGGER.warning(exception)
                errors["base"] = "auth"
            except OgeroApiClientCommunicationError as exception:
                LOGGER.error(exception)
                errors["base"] = "connection"
            except OgeroApiClientError as exception:
                LOGGER.exception(exception)
                errors["base"] = "unknown"
            else:
                self._user_data = user_input
                self._user_data[IS_NEW] = False
                return await self.async_step_account()

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"username": self._user_data[CONF_USERNAME]},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    def _create_client(self, username: str, password: str) -> OgeroApiClient:
        if self._client is None:
            self._client = OgeroApiClient(
                username=username,
                password=password,
                session=async_create_clientsession(self.hass),
            )
        return self._client

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = self._create_client(username, password)
        await client.async_login()

    async def _get_accounts(self, username: str, password: str) -> list[Account]:
        """Validate credentials."""
        client = self._create_client(username, password)
        return await client.async_get_accounts()
