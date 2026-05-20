"""Test Ogero entity registry defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory

from tests.conftest import TEST_ACCOUNT_SERIAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.ogero.data import OgeroConfigEntry


def _registry_entry(hass: HomeAssistant, unique_id: str) -> er.RegistryEntry | None:
    """Return the entity registry entry for an Ogero unique id."""
    entity_id = er.async_get(hass).async_get_entity_id("sensor", "ogero", unique_id)
    if entity_id is None:
        return None
    return er.async_get(hass).async_get(entity_id)


@pytest.mark.usefixtures("mock_api_client")
async def test_diagnostic_entities_disabled_by_default(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Speed and last update are diagnostic and disabled by default."""
    assert loaded_entry.entry_id
    last_update = _registry_entry(hass, f"{TEST_ACCOUNT_SERIAL}_last_update")
    assert last_update is not None
    assert last_update.entity_category is EntityCategory.DIAGNOSTIC
    assert last_update.disabled

    speed = _registry_entry(hass, f"{TEST_ACCOUNT_SERIAL}_speed")
    assert speed is not None
    assert speed.entity_category is EntityCategory.DIAGNOSTIC
    assert speed.disabled


@pytest.mark.usefixtures("mock_api_client")
async def test_primary_sensors_enabled_by_default(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Core usage sensors are enabled by default."""
    assert loaded_entry.entry_id
    for key in ("total_consumption", "quota", "outstanding_balance"):
        reg_entry = _registry_entry(hass, f"{TEST_ACCOUNT_SERIAL}_{key}")
        assert reg_entry is not None
        assert reg_entry.entity_category is None
        assert not reg_entry.disabled
