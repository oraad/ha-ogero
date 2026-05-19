"""Test Ogero sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers import entity_registry as er

from tests.conftest import TEST_SUBENTRY_ID

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _state_for_unique_id(hass: HomeAssistant, unique_id: str) -> str | None:
    """Return state for an entity registry unique id."""
    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", "ogero", unique_id)
    if entry is None:
        return None
    return hass.states.get(entry).state


@pytest.mark.usefixtures("mock_api_client")
async def test_sensors(hass: HomeAssistant, loaded_entry) -> None:
    """Test sensor states after setup."""
    assert (
        _state_for_unique_id(hass, f"{TEST_SUBENTRY_ID}_total_consumption") == "130.0"
    )

    assert _state_for_unique_id(hass, f"{TEST_SUBENTRY_ID}_upload") == "10.0"

    balance_id = er.async_get(hass).async_get_entity_id(
        "sensor", "ogero", f"{TEST_SUBENTRY_ID}_outstanding_balance"
    )
    assert balance_id is not None
    balance = hass.states.get(balance_id)
    assert balance.state == "150000"
    assert balance.attributes.get("unpaid_bills")
