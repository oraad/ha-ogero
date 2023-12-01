"""Adds config flow for Ogero."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    SelectOptionDict,
)

from .api import (
    OgeroApiClient,
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
    OgeroApiClientError,
)
from .const import DOMAIN, LOGGER

ACCOUNT = "account"


class OgeroFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Ogero."""

    VERSION = 1

    _client: OgeroApiClient = None
    _user_data: dict

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
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
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=self._user_data[CONF_USERNAME],
                data={**self._user_data, **user_input},
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

    def _create_client(self, username: str, password: str) -> None:
        if self._client is None:
            self._client = OgeroApiClient(
                username=username,
                password=password,
                session=async_create_clientsession(self.hass),
            )

    async def _test_credentials(self, username: str, password: str):
        """Validate credentials."""
        self._create_client(username, password)
        LOGGER.debug("call async login")
        await self._client.async_login()
        LOGGER.debug("Done async login")

    async def _get_accounts(self, username: str, password: str):
        """Validate credentials."""
        self._create_client(username, password)
        return await self._client.async_get_accounts()
