"""Ogero API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyogero.asyncio import Account as OgeroAccount
from pyogero.asyncio import AuthenticationException, BillInfo, ConsumptionInfo, Ogero
from pyogero.exceptions import OgeroCommunicationError, OgeroParseError

from .const import LOGGER

if TYPE_CHECKING:
    import aiohttp
    from homeassistant.core import HomeAssistant


class OgeroApiClientError(Exception):
    """Exception to indicate a general API error."""


class OgeroApiClientCommunicationError(OgeroApiClientError):
    """Exception to indicate a communication error."""


class OgeroApiClientAuthenticationError(OgeroApiClientError):
    """Exception to indicate an authentication error."""


@dataclass
class Account:
    """Account class."""

    internet: str
    phone: str

    @property
    def serial(self) -> str:
        """Serial value from account."""
        return f"{self.internet}|{self.phone}"

    @staticmethod
    def deserialize(serial: str) -> Account:
        """Deserialize account."""
        internet, phone = serial.split("|", 1)
        return Account(internet=internet, phone=phone)

    def __str__(self) -> str:
        """To string."""
        if self.phone and self.internet:
            return f"DSL# {self.internet} | Phone# {self.phone}"
        if self.phone:
            return f"Phone# {self.phone}"
        if self.internet:
            return f"DSL# {self.internet}"
        return ""

    def __repr__(self) -> str:
        """To repr."""
        return self.__str__()


class AccountMapper:
    """Map between integration and pyogero account types."""

    @staticmethod
    def to_ogero(account: Account | None) -> OgeroAccount | None:
        """Map Account to OgeroAccount."""
        if account is None:
            return None

        return OgeroAccount(phone=account.phone, internet=account.internet)

    @staticmethod
    def from_ogero(account: OgeroAccount) -> Account:
        """Map OgeroAccount to Account."""
        return Account(internet=account.internet, phone=account.phone)


def create_api_client(
    hass: HomeAssistant,
    username: str,
    password: str,
) -> OgeroApiClient:
    """Create an API client using the Home Assistant aiohttp session."""
    return OgeroApiClient(
        username=username,
        password=password,
        session=async_get_clientsession(hass),
    )


class OgeroApiClient:
    """Ogero API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the client."""
        self.ogero_client = Ogero(username, password, session)

    async def async_login(self) -> bool:
        """Login to the API."""
        try:
            return await self.ogero_client.login()
        except AuthenticationException as auth_ex:
            LOGGER.error("Login failed")
            raise OgeroApiClientAuthenticationError(auth_ex.args) from auth_ex
        except OgeroCommunicationError as ex:
            raise OgeroApiClientCommunicationError(str(ex)) from ex
        except OgeroParseError as ex:
            raise OgeroApiClientError(str(ex)) from ex

    async def async_get_accounts(self) -> list[Account]:
        """Get user linked accounts."""
        try:
            accounts = await self.ogero_client.get_accounts()
        except AuthenticationException as auth_ex:
            raise OgeroApiClientAuthenticationError(auth_ex.args) from auth_ex
        except OgeroCommunicationError as ex:
            raise OgeroApiClientCommunicationError(str(ex)) from ex
        except OgeroParseError as ex:
            raise OgeroApiClientError(str(ex)) from ex

        return [AccountMapper.from_ogero(account) for account in accounts]

    async def async_get_bills(self, account: Account) -> BillInfo:
        """Get account bills."""
        _account = AccountMapper.to_ogero(account)
        try:
            bill_infos = await self.ogero_client.get_bill_info(_account)
        except AuthenticationException as auth_ex:
            raise OgeroApiClientAuthenticationError(auth_ex.args) from auth_ex
        except OgeroCommunicationError as ex:
            raise OgeroApiClientCommunicationError(str(ex)) from ex
        except OgeroParseError as ex:
            raise OgeroApiClientError(str(ex)) from ex

        return bill_infos

    async def async_get_consumption(self, account: Account) -> ConsumptionInfo:
        """Get account consumption."""
        _account = AccountMapper.to_ogero(account)
        try:
            consumption_info = await self.ogero_client.get_consumption_info(_account)
        except AuthenticationException as auth_ex:
            raise OgeroApiClientAuthenticationError(auth_ex.args) from auth_ex
        except OgeroCommunicationError as ex:
            raise OgeroApiClientCommunicationError(str(ex)) from ex
        except OgeroParseError as ex:
            raise OgeroApiClientError(str(ex)) from ex

        return consumption_info
