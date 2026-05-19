"""Test Ogero diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.conftest import (
    TEST_ACCOUNT_SERIAL,
    TEST_PASSWORD,
    TEST_SUBENTRY_ID,
    TEST_USERNAME,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.ogero.data import OgeroConfigEntry


@pytest.mark.usefixtures("mock_api_client")
async def test_diagnostics(hass: HomeAssistant, loaded_entry: OgeroConfigEntry) -> None:
    """Test diagnostics redact credentials."""
    result = await hass.config_entries.async_get_diagnostics(loaded_entry.entry_id)
    dumped = str(result)
    assert TEST_PASSWORD not in dumped
    assert TEST_USERNAME not in dumped
    assert result["integration_version"]
    assert len(result["accounts"]) == 1
    assert result["accounts"][0]["subentry_id"] == TEST_SUBENTRY_ID
    assert result["accounts"][0]["account"] == TEST_ACCOUNT_SERIAL
