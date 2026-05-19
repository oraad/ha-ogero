"""Config flow for Ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.selector import (
    DurationSelector,
    DurationSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.util import slugify

from .api import (
    Account,
    OgeroApiClient,
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
    OgeroApiClientError,
    create_api_client,
)
from .const import (
    CONF_ACCOUNT,
    CONF_SCAN_INTERVAL,
    CONFIG_ENTRY_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SUBENTRY_TYPE_ACCOUNT,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .data import OgeroConfigEntry


def _username_unique_id(username: str) -> str:
    """Return a stable unique id for an Ogero login."""
    return cast(str, slugify(username))


@callback  # type: ignore[untyped-decorator]
def _configured_account_serials(entry: OgeroConfigEntry) -> set[str]:
    """Return account serials already configured on this entry."""
    return {
        cast(str, subentry.unique_id)
        for subentry in entry.subentries.values()
        if subentry.subentry_type == SUBENTRY_TYPE_ACCOUNT and subentry.unique_id
    }


class OgeroFlowHandler(ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg,misc]
    """Handle a config flow for Ogero."""

    VERSION = CONFIG_ENTRY_VERSION

    def __init__(self) -> None:
        """Initialize."""
        self._client: OgeroApiClient | None = None
        self._login_data: dict[str, Any] | None = None

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
                self._login_data = user_input
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

    async def async_step_account(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Select the first phone/DSL line for this login."""
        if self._login_data is None:
            return self.async_abort(reason="unknown")

        if user_input is not None:
            account_serial = user_input[CONF_ACCOUNT]
            account = Account.deserialize(account_serial)
            return self.async_create_entry(
                title=self._login_data[CONF_USERNAME],
                data=self._login_data,
                subentries=[
                    {
                        "title": str(account),
                        "data": {CONF_ACCOUNT: account_serial},
                        "subentry_type": SUBENTRY_TYPE_ACCOUNT,
                        "unique_id": account_serial,
                    }
                ],
            )

        client = self._create_client(
            self._login_data[CONF_USERNAME],
            self._login_data[CONF_PASSWORD],
        )
        accounts = await client.async_get_accounts()
        return self.async_show_form(
            step_id="account",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=account.serial,
                                    label=str(account),
                                )
                                for account in accounts
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=CONF_ACCOUNT,
                        ),
                    ),
                }
            ),
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

    @classmethod
    @callback  # type: ignore[untyped-decorator]
    def async_get_supported_subentry_types(
        cls, _config_entry: OgeroConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {SUBENTRY_TYPE_ACCOUNT: AccountSubentryFlowHandler}

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


class AccountSubentryFlowHandler(ConfigSubentryFlow):  # type: ignore[misc]
    """Handle subentry flow for adding and modifying an Ogero line."""

    def __init__(self) -> None:
        """Initialize."""
        self._client: OgeroApiClient | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Add a phone/DSL line."""
        entry = self._get_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            account_serial = user_input[CONF_ACCOUNT]
            if account_serial in _configured_account_serials(entry):
                errors[CONF_ACCOUNT] = "account_already_configured"
            else:
                account = Account.deserialize(account_serial)
                return self.async_create_entry(
                    title=str(account),
                    data={CONF_ACCOUNT: account_serial},
                    unique_id=account_serial,
                )

        accounts = await self._get_accounts(entry)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=account.serial,
                                    label=str(account),
                                )
                                for account in accounts
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=CONF_ACCOUNT,
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> SubentryFlowResult:
        """Reconfigure an existing line."""
        entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}
        if user_input is not None:
            account_serial = user_input[CONF_ACCOUNT]
            configured = _configured_account_serials(entry) - {subentry.unique_id or ""}
            if account_serial in configured:
                errors[CONF_ACCOUNT] = "account_already_configured"
            else:
                account = Account.deserialize(account_serial)
                return self.async_update_and_abort(
                    entry,
                    subentry,
                    title=str(account),
                    data={CONF_ACCOUNT: account_serial},
                    unique_id=account_serial,
                )

        accounts = await self._get_accounts(entry)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCOUNT): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=account.serial,
                                    label=str(account),
                                )
                                for account in accounts
                            ],
                            mode=SelectSelectorMode.DROPDOWN,
                            translation_key=CONF_ACCOUNT,
                        ),
                    ),
                }
            ),
            errors=errors,
        )

    def _create_client(self, entry: OgeroConfigEntry) -> OgeroApiClient:
        if self._client is None:
            self._client = create_api_client(
                self.hass,
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD],
            )
        return self._client

    async def _get_accounts(self, entry: OgeroConfigEntry) -> list[Account]:
        client = self._create_client(entry)
        return await client.async_get_accounts()


class OgeroOptionsFlowHandler(OptionsFlow):  # type: ignore[misc]
    """Handle Ogero options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            scan_interval = user_input.get(CONF_SCAN_INTERVAL)
            if isinstance(scan_interval, dict):
                user_input[CONF_SCAN_INTERVAL] = int(scan_interval["seconds"])
            return self.async_create_entry(data=user_input)

        default_seconds = int(
            self.config_entry.options.get(
                CONF_SCAN_INTERVAL,
                int(DEFAULT_SCAN_INTERVAL.total_seconds()),
            )
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=default_seconds,
                    ): DurationSelector(
                        DurationSelectorConfig(
                            enable_day=False,
                            enable_millisecond=False,
                        ),
                    ),
                }
            ),
        )
