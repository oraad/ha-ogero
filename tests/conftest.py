"""Fixtures for Ogero integration tests."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.util import slugify
from pyogero.types import Bill, BillAmount, BillInfo, BillStatus, ConsumptionInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ogero.api import Account
from custom_components.ogero.const import (
    CONF_ACCOUNT,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    SUBENTRY_TYPE_ACCOUNT,
)

pytest_plugins = ("pytest_homeassistant_custom_component",)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterator

    from homeassistant.core import HomeAssistant

TEST_ACCOUNT_SERIAL = "12345|01234567"
DUAL_ACCOUNT_SUBENTRY_COUNT = 2
TEST_ACCOUNT_SERIAL_2 = "67890|07654321"
TEST_SUBENTRY_ID = "01TESTSUBENTRY00000000001"
TEST_USERNAME = "user"
TEST_PASSWORD = "pass"  # noqa: S105


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> None:
    """Load custom_components for every test."""


@pytest.fixture
def account() -> Account:
    """Return a test account."""
    return Account(internet="12345", phone="01234567")


@pytest.fixture
def consumption_info() -> ConsumptionInfo:
    """Return sample consumption data."""
    return ConsumptionInfo(
        speed="8 Mbps",
        quota=500,
        upload=10.0,
        download=120.0,
        total_consumption=130.0,
        extra_consumption=5.0,
        last_update=datetime(2024, 6, 1, 12, 0, tzinfo=ZoneInfo("Asia/Beirut")),
    )


@pytest.fixture
def bill_info() -> BillInfo:
    """Return sample bill data."""
    return BillInfo(
        total_outstanding=BillAmount(amount=150000, currency="LBP"),
        bills=[
            Bill(
                date=datetime(2024, 5, 1),  # noqa: DTZ001
                amount=BillAmount(amount=75000, currency="LBP"),
                status=BillStatus.UNPAID,
            ),
        ],
    )


@pytest.fixture
def mock_setup_entry() -> AsyncGenerator[AsyncMock]:
    """Prevent full setup during config flow tests."""
    with patch(
        "custom_components.ogero.async_setup_entry",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_setup:
        yield mock_setup


@pytest.fixture(name="mock_api_client")
def _mock_api_client(
    consumption_info: ConsumptionInfo,
    bill_info: BillInfo,
) -> Iterator[MagicMock]:
    """Patch API client factory with successful responses."""
    accounts = [
        Account(internet="12345", phone="01234567"),
        Account(internet="67890", phone="07654321"),
    ]
    mock_client = MagicMock()
    mock_client.async_login = AsyncMock(return_value=True)
    mock_client.async_get_accounts = AsyncMock(return_value=accounts)
    mock_client.async_get_consumption = AsyncMock(return_value=consumption_info)
    mock_client.async_get_bills = AsyncMock(return_value=bill_info)
    with (
        patch(
            "custom_components.ogero.config_flow.create_api_client",
            return_value=mock_client,
        ),
        patch(
            "custom_components.ogero.__init__.create_api_client",
            return_value=mock_client,
        ),
    ):
        yield mock_client


@pytest.fixture
def parent_config_data() -> dict[str, str]:
    """Return parent config entry data."""
    return {
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    }


@pytest.fixture
def subentries_data() -> tuple[dict[str, Any], ...]:
    """Return account subentry data for tests."""
    return (
        {
            "data": {CONF_ACCOUNT: TEST_ACCOUNT_SERIAL},
            "subentry_id": TEST_SUBENTRY_ID,
            "subentry_type": SUBENTRY_TYPE_ACCOUNT,
            "title": "DSL# 12345 | Phone# 01234567",
            "unique_id": TEST_ACCOUNT_SERIAL,
        },
    )


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant,
    parent_config_data: dict[str, str],
    subentries_data: tuple[dict[str, Any], ...],
    mock_api_client: MagicMock,  # noqa: ARG001
) -> MockConfigEntry:
    """Set up a v2 config entry with one account subentry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_USER,
        data=parent_config_data,
        unique_id=slugify(TEST_USERNAME),
        version=CONFIG_ENTRY_VERSION,
        subentries_data=subentries_data,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
