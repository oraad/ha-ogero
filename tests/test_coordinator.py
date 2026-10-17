"""Test Ogero data update coordinator."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from pyogero.types import ConsumptionInfo

from tests.conftest import TEST_ACCOUNT_SERIAL, TEST_QUOTA, TEST_TOTAL_CONSUMPTION

if TYPE_CHECKING:
    from custom_components.ogero.data import OgeroConfigEntry


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_usage_is_percentage_of_quota(loaded_entry: OgeroConfigEntry) -> None:
    """Usage is the percentage of the quota consumed."""
    coordinator = loaded_entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    await coordinator.async_refresh()
    assert coordinator.data is not None
    assert coordinator.data.usage == pytest.approx(
        TEST_TOTAL_CONSUMPTION / TEST_QUOTA * 100
    )


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_usage_is_zero_for_unlimited_quota(
    loaded_entry: OgeroConfigEntry,
) -> None:
    """Usage is 0 (not unknown) when the quota is unlimited."""
    coordinator = loaded_entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    loaded_entry.runtime_data.client.async_get_consumption = AsyncMock(
        return_value=ConsumptionInfo(
            quota=math.inf, total_consumption=TEST_TOTAL_CONSUMPTION
        )
    )
    await coordinator.async_refresh()
    assert coordinator.data is not None
    assert coordinator.data.quota == "Unlimited"
    assert coordinator.data.usage == 0.0
