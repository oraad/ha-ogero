"""Shared platform setup helpers."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, cast

from .const import (
    CONF_DISABLED_ACCOUNTS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import OgeroDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import Account
    from .data import OgeroConfigEntry


def get_update_interval(entry: OgeroConfigEntry) -> timedelta:
    """Return the configured poll interval."""
    if not entry.options or CONF_SCAN_INTERVAL not in entry.options:
        return DEFAULT_SCAN_INTERVAL
    raw = entry.options[CONF_SCAN_INTERVAL]
    try:
        seconds = int(raw)
    except TypeError, ValueError:
        return DEFAULT_SCAN_INTERVAL
    lo = int(MIN_SCAN_INTERVAL.total_seconds())
    hi = int(MAX_SCAN_INTERVAL.total_seconds())
    seconds = max(lo, min(seconds, hi))
    return timedelta(seconds=seconds)


def get_disabled_account_serials(entry: OgeroConfigEntry) -> set[str]:
    """Return account serials the user removed (device delete) and do not recreate."""
    raw = entry.options.get(CONF_DISABLED_ACCOUNTS)
    if not raw or not isinstance(raw, list):
        return set()
    return {str(x) for x in raw}


async def async_fetch_accounts(
    _hass: HomeAssistant, entry: OgeroConfigEntry
) -> list[Account]:
    """Return all phone/DSL lines for this login from the Ogero API."""
    client = entry.runtime_data.client
    await client.async_login()
    return cast("list[Account]", await client.async_get_accounts())


async def async_setup_account_coordinators(
    hass: HomeAssistant,
    entry: OgeroConfigEntry,
    update_interval: timedelta,
) -> list[tuple[Account, OgeroDataUpdateCoordinator]]:
    """Create or refresh coordinators for each active API account."""
    runtime = entry.runtime_data
    accounts = await async_fetch_accounts(hass, entry)
    disabled = get_disabled_account_serials(entry)
    active_serials = {a.serial for a in accounts if a.serial not in disabled}

    for key in list(runtime.coordinators):
        if key not in active_serials:
            await runtime.coordinators[key].async_shutdown()
            del runtime.coordinators[key]

    coordinators: list[tuple[Account, OgeroDataUpdateCoordinator]] = []
    for account in accounts:
        if account.serial in disabled:
            continue
        if account.serial in runtime.coordinators:
            coordinators.append((account, runtime.coordinators[account.serial]))
            continue
        coordinator = OgeroDataUpdateCoordinator(
            hass,
            entry,
            account,
            account.serial,
            update_interval=update_interval,
        )
        await coordinator.async_config_entry_first_refresh()
        runtime.coordinators[account.serial] = coordinator
        coordinators.append((account, coordinator))

    return coordinators
