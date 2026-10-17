"""Test Ogero sensors."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.ogero.const import UNLIMITED_QUOTA
from custom_components.ogero.sensor import ENTITY_DESCRIPTIONS, QUOTA, OgeroSensor
from tests.conftest import TEST_ACCOUNT_SERIAL, TEST_QUOTA

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.ogero.data import OgeroConfigEntry


def _state_for_unique_id(hass: HomeAssistant, unique_id: str) -> str | None:
    """Return state for an entity registry unique id."""
    entity_reg = er.async_get(hass)
    entry = entity_reg.async_get_entity_id("sensor", "ogero", unique_id)
    if entry is None:
        return None
    return hass.states.get(entry).state


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_sensors(hass: HomeAssistant) -> None:
    """Test sensor states after setup."""
    assert (
        _state_for_unique_id(hass, f"{TEST_ACCOUNT_SERIAL}_total_consumption")
        == "130.0"
    )

    assert (
        _state_for_unique_id(hass, f"{TEST_ACCOUNT_SERIAL}_extra_consumption") == "5.0"
    )

    balance_id = er.async_get(hass).async_get_entity_id(
        "sensor", "ogero", f"{TEST_ACCOUNT_SERIAL}_outstanding_balance"
    )
    assert balance_id is not None
    balance = hass.states.get(balance_id)
    assert balance.state == "150000"
    assert balance.attributes.get("unpaid_bills")


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_sensor_stays_available_when_last_poll_failed(
    loaded_entry: OgeroConfigEntry,
) -> None:
    """After a failed poll, last snapshot remains; entity stays available."""
    coordinator = loaded_entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    assert coordinator.data is not None
    coordinator.last_update_success = False

    desc = next(d for d in ENTITY_DESCRIPTIONS if d.key == QUOTA)
    sensor = OgeroSensor(coordinator, coordinator.account, desc)
    assert sensor.available is True


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_sensor_unavailable_when_coordinator_has_no_data(
    loaded_entry: OgeroConfigEntry,
) -> None:
    """Without coordinator data, entity is unavailable."""
    coordinator = loaded_entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    desc = next(d for d in ENTITY_DESCRIPTIONS if d.key == QUOTA)
    empty_coordinator = MagicMock()
    empty_coordinator.data = None
    sensor = OgeroSensor(empty_coordinator, coordinator.account, desc)
    assert sensor.available is False


@pytest.mark.usefixtures("mock_api_client", "loaded_entry")
async def test_quota_sensor_shows_unlimited_text(
    hass: HomeAssistant,
    loaded_entry: OgeroConfigEntry,
) -> None:
    """Quota sensor displays 'Unlimited' and drops the GB unit when unlimited."""
    coordinator = loaded_entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    assert coordinator.data is not None
    desc = next(d for d in ENTITY_DESCRIPTIONS if d.key == QUOTA)
    sensor = OgeroSensor(coordinator, coordinator.account, desc)

    # Numeric quota keeps the GB unit and display precision.
    assert sensor.native_value == TEST_QUOTA
    assert sensor.native_unit_of_measurement == "GB"
    assert sensor.suggested_display_precision == 0

    # Unlimited plan shows text and drops the numeric unit/precision so Home
    # Assistant accepts the non-numeric state.
    coordinator.async_set_updated_data(replace(coordinator.data, quota=UNLIMITED_QUOTA))
    await hass.async_block_till_done()
    assert sensor.native_value == "Unlimited"
    assert sensor.native_unit_of_measurement is None
    assert sensor.suggested_display_precision is None
    assert _state_for_unique_id(hass, f"{TEST_ACCOUNT_SERIAL}_quota") == "Unlimited"
