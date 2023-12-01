"""Sample API Client."""
from __future__ import annotations

from dataclasses import dataclass

import asyncio
import socket

import aiohttp
import async_timeout

from pyogero.asyncio import Ogero, Account as OgeroAccount, AuthenticationException
from pyogero.types import BillStatus

from .const import LOGGER


class OgeroApiClientError(Exception):
    """Exception to indicate a general API error."""


class OgeroApiClientCommunicationError(OgeroApiClientError):
    """Exception to indicate a communication error."""


class OgeroApiClientAuthenticationError(OgeroApiClientError):
    """Exception to indicate an authentication error."""


@dataclass
class Account:
    internet: str
    phone: str

    @property
    def serial(self):
        return f"{self.internet}|{self.phone}"

    @staticmethod
    def deserialize(serial: str):
        internet, phone = serial.split("|")
        return Account(internet, phone)

    def __str__(self) -> str:
        if self.phone is not None and self.internet is not None:
            return f"DSL# {self.internet} | Phone# {self.phone}"
        elif self.phone is not None:
            return f"Phone# {self.phone}"
        elif self.internet is not None:
            return f"DSL# {self.internet}"
        else:
            return ""

    def __repr__(self) -> str:
        return self.__str__()


class AccountMapper:
    @staticmethod
    def toOgero(account: Account):
        if account is None:
            return None

        _account = OgeroAccount()
        _account.internet = account.internet
        _account.phone = account.phone
        return _account

    def fromOgero(account: OgeroAccount):
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

    async def async_login(self):
        try:
            return await self.ogero_client.login()
        except AuthenticationException as authEx:
            LOGGER.error("login failed")
            raise OgeroApiClientAuthenticationError(authEx.args)

    async def async_get_accounts(self, account: Account = None):
        _account = AccountMapper.toOgero(account)
        accounts = await self.ogero_client.get_accounts(_account)
        return [AccountMapper.fromOgero(account) for account in accounts]

    async def async_get_bills(self, account: Account):
        _account = AccountMapper.toOgero(account)
        bill_infos = await self.ogero_client.get_bill_info(_account)
        return bill_infos

    async def async_get_consumption(self, account: Account):
        _account = AccountMapper.toOgero(account)
        consumption_info = await self.ogero_client.get_consumption_info(_account)
        return consumption_info

    # async def async_get_data(self) -> any:
    #     """Get data from the API."""
    #     return await self._api_wrapper(
    #         method="get", url="https://jsonplaceholder.typicode.com/posts/1"
    #     )

    # async def async_set_title(self, value: str) -> any:
    #     """Get data from the API."""
    #     return await self._api_wrapper(
    #         method="patch",
    #         url="https://jsonplaceholder.typicode.com/posts/1",
    #         data={"title": value},
    #         headers={"Content-type": "application/json; charset=UTF-8"},
    #     )

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        data: dict | None = None,
        headers: dict | None = None,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data,
                )
                if response.status in (401, 403):
                    raise OgeroApiClientAuthenticationError(
                        "Invalid credentials",
                    )
                response.raise_for_status()
                return await response.json()

        except asyncio.TimeoutError as exception:
            raise OgeroApiClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise OgeroApiClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise OgeroApiClientError("Something really wrong happened!") from exception
