"""DataUpdateCoordinator for ogero."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pyogero.types import BillStatus

from .api import Account, OgeroApiClientAuthenticationError, OgeroApiClientError
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from datetime import datetime, timedelta

    from homeassistant.core import HomeAssistant

    from .data import OgeroConfigEntry


@dataclass
class OgeroCoordinatorData:
    """Data returned by the coordinator."""

    quota: int
    speed: str
    upload: float
    download: float
    total_consumption: float
    extra_consumption: float
    last_update: datetime | None
    outstanding_balance: int
    unpaid_bills: list[dict[str, str]]
    has_unpaid_bills: bool
    has_extra_consumption: bool


class OgeroDataUpdateCoordinator(DataUpdateCoordinator[OgeroCoordinatorData]):  # type: ignore[misc]
    """Fetch Ogero account data for all entities."""

    config_entry: OgeroConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: OgeroConfigEntry,
        account: Account,
        subentry_id: str,
        *,
        update_interval: timedelta,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name=f"{DOMAIN}_{subentry_id}",
            update_interval=update_interval,
            config_entry=config_entry,
        )
        self.account = account
        self.subentry_id = subentry_id

    async def _async_update_data(self) -> OgeroCoordinatorData:
        """Update data via the API client."""
        client = self.config_entry.runtime_data.client
        try:
            consumption = await client.async_get_consumption(self.account)
            bill_info = await client.async_get_bills(self.account)
        except OgeroApiClientAuthenticationError as exception:
            raise ConfigEntryAuthFailed(exception) from exception
        except OgeroApiClientError as exception:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="poll_failed",
            ) from exception

        unpaid_bills = [
            {
                "period": bill.date.strftime("%Y-%m"),
                "amount": f"{bill.amount.currency} {int(bill.amount.amount)}",
                "status": bill.status.name,
            }
            for bill in bill_info.bills
            if bill.status == BillStatus.UNPAID
        ]

        has_unpaid_bills = any(
            bill.status == BillStatus.UNPAID for bill in bill_info.bills
        )
        extra_consumption = consumption.extra_consumption

        return OgeroCoordinatorData(
            quota=consumption.quota,
            last_update=consumption.last_update,
            speed=consumption.speed,
            upload=consumption.upload,
            download=consumption.download,
            total_consumption=consumption.total_consumption,
            extra_consumption=extra_consumption,
            outstanding_balance=int(bill_info.total_outstanding.amount),
            unpaid_bills=unpaid_bills,
            has_unpaid_bills=has_unpaid_bills,
            has_extra_consumption=extra_consumption > 0,
        )
