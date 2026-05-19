"""Test Ogero config entry migration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.util import slugify
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ogero.const import (
    CONF_ACCOUNT,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    SUBENTRY_TYPE_ACCOUNT,
)
from custom_components.ogero.migrate import async_migrate_entry
from tests.conftest import (
    DUAL_ACCOUNT_SUBENTRY_COUNT,
    TEST_ACCOUNT_SERIAL,
    TEST_PASSWORD,
    TEST_USERNAME,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


@pytest.mark.usefixtures("mock_api_client")
async def test_migrate_merge_same_username(hass: HomeAssistant) -> None:
    """Two v1 entries with the same username merge into one v2 parent."""
    account_b = "99999|09999999"
    entry_a = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        source=SOURCE_USER,
        unique_id=TEST_ACCOUNT_SERIAL,
        data={
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_ACCOUNT: TEST_ACCOUNT_SERIAL,
        },
        entry_id="entry_a",
    )
    entry_b = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        source=SOURCE_USER,
        unique_id=account_b,
        data={
            CONF_USERNAME: TEST_USERNAME,
            CONF_PASSWORD: TEST_PASSWORD,
            CONF_ACCOUNT: account_b,
        },
        entry_id="entry_b",
    )
    entry_a.add_to_hass(hass)
    entry_b.add_to_hass(hass)

    migrated_entry_a = hass.config_entries.async_get_entry(entry_a.entry_id)
    migrated_entry_b = hass.config_entries.async_get_entry(entry_b.entry_id)
    assert migrated_entry_a is not None
    assert migrated_entry_b is not None

    assert await async_migrate_entry(hass, migrated_entry_a)
    assert await async_migrate_entry(hass, migrated_entry_b)
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    parent = entries[0]
    assert parent.version == CONFIG_ENTRY_VERSION
    assert parent.unique_id == slugify(TEST_USERNAME)
    assert CONF_ACCOUNT not in parent.data
    assert len(parent.subentries) == DUAL_ACCOUNT_SUBENTRY_COUNT

    serials = {
        sub.unique_id
        for sub in parent.subentries.values()
        if sub.subentry_type == SUBENTRY_TYPE_ACCOUNT
    }
    assert serials == {TEST_ACCOUNT_SERIAL, account_b}
