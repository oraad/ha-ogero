"""Test the Ogero config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ogero import async_remove_config_entry_device
from custom_components.ogero.api import (
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
)
from custom_components.ogero.const import (
    CONF_DISABLED_ACCOUNTS,
    CONF_SCAN_INTERVAL,
    CONFIG_ENTRY_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from custom_components.ogero.sensor import ENTITY_DESCRIPTIONS
from tests.conftest import (
    TEST_ACCOUNT_SERIAL,
    TEST_ACCOUNT_SERIAL_2,
    TEST_PASSWORD,
    TEST_USERNAME,
)

CUSTOM_SCAN_INTERVAL_SECONDS = 1800

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.ogero.data import OgeroConfigEntry


@pytest.mark.usefixtures("mock_api_client", "mock_setup_entry")
async def test_user_flow(hass: HomeAssistant) -> None:
    """Test login creates a credentials-only config entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME, CONF_PASSWORD: TEST_PASSWORD},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USERNAME
    assert result["data"] == {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    assert result["version"] == CONFIG_ENTRY_VERSION

    entry = result["result"]
    assert len(entry.subentries) == 0
    assert entry.version == CONFIG_ENTRY_VERSION


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test invalid credentials."""
    with patch("custom_components.ogero.api.create_api_client") as mock_create:
        mock_client = mock_create.return_value
        mock_client.async_login = AsyncMock(
            side_effect=OgeroApiClientAuthenticationError("auth failed")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: TEST_USERNAME, CONF_PASSWORD: "wrong"},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test connection errors."""
    with patch("custom_components.ogero.api.create_api_client") as mock_create:
        mock_client = mock_create.return_value
        mock_client.async_login = AsyncMock(
            side_effect=OgeroApiClientCommunicationError("offline")
        )

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_USERNAME: TEST_USERNAME, CONF_PASSWORD: TEST_PASSWORD},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.usefixtures("mock_api_client")
async def test_duplicate_login(hass: HomeAssistant, parent_config_data: dict) -> None:
    """Test duplicate username is rejected."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data=parent_config_data,
        unique_id=slugify(TEST_USERNAME),
        version=CONFIG_ENTRY_VERSION,
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME, CONF_PASSWORD: TEST_PASSWORD},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.usefixtures("mock_api_client")
async def test_options_flow_updates_interval(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Test options flow saves scan interval and reloads the entry."""
    entry = loaded_entry
    coordinator = entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    default_seconds = int(DEFAULT_SCAN_INTERVAL.total_seconds())
    assert coordinator.update_interval.total_seconds() == default_seconds

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: {"seconds": CUSTOM_SCAN_INTERVAL_SECONDS}},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == CUSTOM_SCAN_INTERVAL_SECONDS

    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    assert entry.options[CONF_SCAN_INTERVAL] == CUSTOM_SCAN_INTERVAL_SECONDS
    coordinator = entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    assert coordinator.update_interval.total_seconds() == CUSTOM_SCAN_INTERVAL_SECONDS


@pytest.mark.usefixtures("mock_api_client")
async def test_options_flow_duration_dict_hours_minutes_seconds(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """DurationSelector sends a full period dict; minutes must count, not seconds alone."""
    entry = loaded_entry
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: {
                "days": 0,
                "hours": 0,
                "minutes": 45,
                "seconds": 0,
                "milliseconds": 0,
            },
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == 45 * 60

    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    assert coordinator.update_interval.total_seconds() == 45 * 60


@pytest.mark.usefixtures("mock_api_client")
async def test_options_flow_clamps_below_minimum(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Intervals below the minimum are stored and applied as the minimum."""
    entry = loaded_entry
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: {
                "days": 0,
                "hours": 0,
                "minutes": 5,
                "seconds": 0,
                "milliseconds": 0,
            },
        },
    )
    min_seconds = int(MIN_SCAN_INTERVAL.total_seconds())
    assert result["data"][CONF_SCAN_INTERVAL] == min_seconds

    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    coordinator = entry.runtime_data.coordinators[TEST_ACCOUNT_SERIAL]
    assert coordinator.update_interval.total_seconds() == min_seconds


@pytest.mark.usefixtures("mock_api_client", "mock_setup_entry")
async def test_reauth_flow(
    hass: HomeAssistant,
    parent_config_data: dict,
) -> None:
    """Test reauthentication updates credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=parent_config_data,
        unique_id=slugify(TEST_USERNAME),
        version=CONFIG_ENTRY_VERSION,
    )
    entry.add_to_hass(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    new_password = "newpass"  # noqa: S105
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME, CONF_PASSWORD: new_password},
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    assert entry.data[CONF_PASSWORD] == new_password


@pytest.mark.usefixtures("mock_api_client")
async def test_all_api_accounts_have_coordinators_and_entities(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Each account returned by the API gets a coordinator and full sensor set."""
    entry = loaded_entry
    assert set(entry.runtime_data.coordinators) == {
        TEST_ACCOUNT_SERIAL,
        TEST_ACCOUNT_SERIAL_2,
    }

    entity_reg = er.async_get(hass)
    sensor_entities = [
        entity
        for entity in entity_reg.entities.values()
        if entity.config_entry_id == entry.entry_id and entity.domain == "sensor"
    ]
    account_count = len(entry.runtime_data.coordinators)
    assert len(sensor_entities) == len(ENTITY_DESCRIPTIONS) * account_count


@pytest.mark.usefixtures("mock_api_client")
async def test_remove_device_adds_disabled_account(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Deleting a line device stores its serial in disabled_accounts."""
    entry = loaded_entry
    device_reg = dr.async_get(hass)
    device = device_reg.async_get_device(identifiers={(DOMAIN, TEST_ACCOUNT_SERIAL)})
    assert device is not None

    assert await async_remove_config_entry_device(hass, entry, device)
    await hass.async_block_till_done()

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    disabled = entry.options.get(CONF_DISABLED_ACCOUNTS, [])
    assert TEST_ACCOUNT_SERIAL in disabled
