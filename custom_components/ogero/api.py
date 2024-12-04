"""Sample API Client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pyogero.asyncio import Account as OgeroAccount
from pyogero.asyncio import AuthenticationException, BillInfo, ConsumptionInfo, Ogero

from .const import LOGGER

if TYPE_CHECKING:
    import aiohttp


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
        internet, phone = serial.split("|")
        return Account(internet, phone)

    def __str__(self) -> str:
        """To string."""
        s = ""
        if self.phone is not None and self.internet is not None:
            s = f"DSL# {self.internet} | Phone# {self.phone}"
        elif self.phone is not None:
            s = f"Phone# {self.phone}"
        elif self.internet is not None:
            s = f"DSL# {self.internet}"

        return s

    def __repr__(self) -> str:
        """To repr."""
        return self.__str__()


class AccountMapper:
    """Account Mapper."""

    @staticmethod
    def to_ogero(account: Account | None) -> OgeroAccount | None:
        """Map Account to OgeroAccount."""
        if account is None:
            return None

        _account = OgeroAccount()
        _account.internet = account.internet
        _account.phone = account.phone
        return _account

    @staticmethod
    def from_ogero(account: OgeroAccount) -> Account:
        """Map OgeroAccount to Account."""
        if account is None:
            return None
        return Account(account.internet, account.phone)


class OgeroApiClient:
    """Ogero API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Ogero API Client."""
        self.ogero_client = Ogero(username, password, session)

    async def async_login(self) -> bool:
        """Login to api."""
        try:
            return await self.ogero_client.login()
        except AuthenticationException as authEx:
            LOGGER.error("login failed")
            raise OgeroApiClientAuthenticationError(authEx.args) from None

    async def async_get_accounts(self, account: Account | None = None) -> list[Account]:
        """Get user linked accounts."""
        _account = AccountMapper.to_ogero(account)
        accounts = await self.ogero_client.get_accounts(_account)
        if accounts is None:
            msg = "No account found."
            raise OgeroApiClientError(msg) from None
        return [AccountMapper.from_ogero(account) for account in accounts]

    async def async_get_bills(self, account: Account) -> BillInfo:
        """Get account bills."""
        _account = AccountMapper.to_ogero(account)
        bill_infos = await self.ogero_client.get_bill_info(_account)
        if bill_infos is None:
            msg = "No bill Info found."
            raise OgeroApiClientError(msg)
        return bill_infos

    async def async_get_consumption(self, account: Account) -> ConsumptionInfo:
        """Get account consumption."""
        _account = AccountMapper.to_ogero(account)
        consumption_info = await self.ogero_client.get_consumption_info(_account)
        if consumption_info is None:
            msg = "No consumption info found."
            raise OgeroApiClientError(msg)
        return consumption_info
