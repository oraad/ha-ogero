"""DataUpdateCoordinator for ogero."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, TypedDict

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from pyogero.types import BillStatus

from .api import (
    Account,
    OgeroApiClient,
    OgeroApiClientAuthenticationError,
    OgeroApiClientError,
)
from .const import DOMAIN, LOGGER
from .device_info import OgeroDeviceInfo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


class StateAttribute(TypedDict):
    """Device state attribute."""

    outstanding_balance: list[tuple]


class Data(TypedDict):
    """Device data."""

    quota: int
    last_update: datetime
    speed: str
    total_consumption: float
    extra_consumption: float
    outstanding_balance: float
    state_attributes: StateAttribute


# https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
class OgeroDataUpdateCoordinator(DataUpdateCoordinator[Data]):
    """Class to manage fetching data from the API."""

    config_entry: ConfigEntry
    _device: OgeroDeviceInfo

    def __init__(
        self,
        hass: HomeAssistant,
        client: OgeroApiClient,
        account: Account,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

        self.client = client
        self.account = account
        self._device = OgeroDeviceInfo(hass, self.config_entry, account.phone)

    @property
    def device(self) -> OgeroDeviceInfo:
        """Get device info."""
        return self._device

    async def _get_account_info(self) -> Data:
        try:
            consumption = await self.client.async_get_consumption(self.account)
            bill_info = await self.client.async_get_bills(self.account)

            bills_history = [
                (
                    bill.date.strftime("%Y-%m"),
                    f"{bill.amount.currency} {int(bill.amount.amount)} ({bill.status.name})",  # noqa: E501
                )
                for bill in bill_info.bills
                if bill.status == BillStatus.UNPAID
            ]

            data: Data = {
                "quota": consumption.quota,
                "last_update": consumption.last_update,
                "speed": consumption.speed,
                "total_consumption": consumption.total_consumption,
                "extra_consumption": consumption.extra_consumption,
                "outstanding_balance": int(bill_info.total_outstanding.amount),
                "state_attributes": {"outstanding_balance": bills_history},
            }

        except OgeroApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OgeroApiClientError as exception:
            raise UpdateFailed(exception) from exception
        else:
            LOGGER.debug("data: %s", data)
            return data

    async def _async_update_data(self) -> Data:
        """Update data via library."""
        return await self._get_account_info()
