"""Shared platform setup helpers."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from .api import Account
from .const import (
    CONF_ACCOUNT,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    SUBENTRY_TYPE_ACCOUNT,
)
from .coordinator import OgeroDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant

    from .data import OgeroConfigEntry


def get_update_interval(entry: OgeroConfigEntry) -> timedelta:
    """Return the configured poll interval."""
    if entry.options and CONF_SCAN_INTERVAL in entry.options:
        return timedelta(seconds=entry.options[CONF_SCAN_INTERVAL])
    return DEFAULT_SCAN_INTERVAL


async def async_setup_account_coordinators(
    hass: HomeAssistant,
    entry: OgeroConfigEntry,
    update_interval: timedelta,
) -> list[tuple[ConfigSubentry, OgeroDataUpdateCoordinator]]:
    """Create coordinators for each account subentry."""
    runtime = entry.runtime_data
    coordinators: list[tuple[ConfigSubentry, OgeroDataUpdateCoordinator]] = []

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_ACCOUNT:
            continue

        account = Account.deserialize(subentry.data[CONF_ACCOUNT])
        coordinator = OgeroDataUpdateCoordinator(
            hass,
            entry,
            account,
            subentry.subentry_id,
            update_interval=update_interval,
        )
        await coordinator.async_config_entry_first_refresh()
        runtime.coordinators[subentry.subentry_id] = coordinator
        coordinators.append((subentry, coordinator))

    return coordinators
