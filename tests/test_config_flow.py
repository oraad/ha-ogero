"""Test the Ogero config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ogero.api import (
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
)
from custom_components.ogero.const import (
    CONF_ACCOUNT,
    CONF_SCAN_INTERVAL,
    CONFIG_ENTRY_VERSION,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SUBENTRY_TYPE_ACCOUNT,
)
from custom_components.ogero.sensor import ENTITY_DESCRIPTIONS
from tests.conftest import (
    DUAL_ACCOUNT_SUBENTRY_COUNT,
    TEST_ACCOUNT_SERIAL,
    TEST_ACCOUNT_SERIAL_2,
    TEST_PASSWORD,
    TEST_SUBENTRY_ID,
    TEST_USERNAME,
)

CUSTOM_SCAN_INTERVAL_SECONDS = 1800

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from custom_components.ogero.data import OgeroConfigEntry


@pytest.mark.usefixtures("mock_api_client", "mock_setup_entry")
async def test_user_flow(hass: HomeAssistant) -> None:
    """Test login creates parent entry and chains subentry flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_USERNAME: TEST_USERNAME, CONF_PASSWORD: TEST_PASSWORD},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "account"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_ACCOUNT: TEST_ACCOUNT_SERIAL},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_USERNAME
    assert result["data"] == {
        CONF_USERNAME: TEST_USERNAME,
        CONF_PASSWORD: TEST_PASSWORD,
    }
    assert result["version"] == CONFIG_ENTRY_VERSION

    entry = result["result"]
    assert len(entry.subentries) == 1
    subentry = next(iter(entry.subentries.values()))
    assert subentry.title == "DSL# 12345 | Phone# 01234567"
    assert subentry.data[CONF_ACCOUNT] == TEST_ACCOUNT_SERIAL


async def test_user_flow_invalid_auth(hass: HomeAssistant) -> None:
    """Test invalid credentials."""
    with patch("custom_components.ogero.config_flow.create_api_client") as mock_create:
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
    with patch("custom_components.ogero.config_flow.create_api_client") as mock_create:
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
async def test_duplicate_account_subentry(
    hass: HomeAssistant,
    parent_config_data: dict,
    subentries_data: tuple,
) -> None:
    """Test duplicate account on the same parent is rejected."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data=parent_config_data,
        unique_id=slugify(TEST_USERNAME),
        version=CONFIG_ENTRY_VERSION,
        subentries_data=subentries_data,
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.subentries.async_init(
        (existing.entry_id, SUBENTRY_TYPE_ACCOUNT),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_ACCOUNT: TEST_ACCOUNT_SERIAL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_ACCOUNT: "account_already_configured"}


@pytest.mark.usefixtures("mock_api_client")
async def test_options_flow_updates_interval(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Test options flow saves scan interval and reloads the entry."""
    entry = loaded_entry
    coordinator = entry.runtime_data.coordinators[TEST_SUBENTRY_ID]
    default_seconds = int(DEFAULT_SCAN_INTERVAL.total_seconds())
    assert coordinator.update_interval.total_seconds() == default_seconds

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: CUSTOM_SCAN_INTERVAL_SECONDS},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_SCAN_INTERVAL] == CUSTOM_SCAN_INTERVAL_SECONDS

    await hass.async_block_till_done(wait_background_tasks=True)

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    assert entry.options[CONF_SCAN_INTERVAL] == CUSTOM_SCAN_INTERVAL_SECONDS
    coordinator = entry.runtime_data.coordinators[TEST_SUBENTRY_ID]
    assert coordinator.update_interval.total_seconds() == CUSTOM_SCAN_INTERVAL_SECONDS


@pytest.mark.usefixtures("mock_api_client", "mock_setup_entry")
async def test_reauth_flow(
    hass: HomeAssistant,
    parent_config_data: dict,
    subentries_data: tuple,
) -> None:
    """Test reauthentication updates credentials."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=parent_config_data,
        unique_id=slugify(TEST_USERNAME),
        version=CONFIG_ENTRY_VERSION,
        subentries_data=subentries_data,
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
async def test_add_second_account_subentry(
    hass: HomeAssistant, loaded_entry: OgeroConfigEntry
) -> None:
    """Test adding a second line creates coordinators and entities."""
    entry = loaded_entry
    assert len(entry.runtime_data.coordinators) == 1

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_ACCOUNT),
        context={"source": config_entries.SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {CONF_ACCOUNT: TEST_ACCOUNT_SERIAL_2},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY

    await hass.async_block_till_done(wait_background_tasks=True)

    entry = hass.config_entries.async_get_entry(entry.entry_id)
    assert entry is not None
    account_count = len(entry.subentries)
    assert account_count == DUAL_ACCOUNT_SUBENTRY_COUNT
    assert len(entry.runtime_data.coordinators) == account_count

    entity_reg = er.async_get(hass)
    sensor_entities = [
        entity
        for entity in entity_reg.entities.values()
        if entity.config_entry_id == entry.entry_id and entity.platform == "sensor"
    ]
    assert len(sensor_entities) == len(ENTITY_DESCRIPTIONS) * account_count
