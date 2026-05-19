"""Test Ogero binary sensors."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers import entity_registry as er

from tests.conftest import TEST_SUBENTRY_ID

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _state_for_unique_id(
    hass: HomeAssistant, domain: str, unique_id: str
) -> str | None:
    """Return state for an entity registry unique id."""
    entity_id = er.async_get(hass).async_get_entity_id(domain, "ogero", unique_id)
    if entity_id is None:
        return None
    return hass.states.get(entity_id).state


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_binary_sensors(hass: HomeAssistant) -> None:
    """Test binary sensor states."""
    assert (
        _state_for_unique_id(hass, "binary_sensor", f"{TEST_SUBENTRY_ID}_unpaid_bills")
        == "on"
    )
    assert (
        _state_for_unique_id(hass, "binary_sensor", f"{TEST_SUBENTRY_ID}_over_quota")
        == "on"
    )
