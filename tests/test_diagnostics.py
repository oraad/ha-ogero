"""Test Ogero diagnostics."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from custom_components.ogero.diagnostics import async_get_config_entry_diagnostics
from tests.conftest import (
    TEST_ACCOUNT_SERIAL,
    TEST_ACCOUNT_SERIAL_2,
    TEST_PASSWORD,
    TEST_USERNAME,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.ogero.data import OgeroConfigEntry


@pytest.mark.usefixtures("mock_api_client")
async def test_diagnostics(hass: HomeAssistant, loaded_entry: OgeroConfigEntry) -> None:
    """Test diagnostics redact credentials."""
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)
    dumped = str(result)
    assert TEST_PASSWORD not in dumped
    assert TEST_USERNAME not in dumped
    assert result["integration_version"]
    assert len(result["accounts"]) == 2
    serials = {acc["account_serial"] for acc in result["accounts"]}
    assert serials == {TEST_ACCOUNT_SERIAL, TEST_ACCOUNT_SERIAL_2}
