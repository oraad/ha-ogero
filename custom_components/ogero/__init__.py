"""Custom integration to integrate Ogero Telekom with Home Assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.loader import async_get_loaded_integration

from .api import create_api_client
from .const import DOMAIN
from .data import OgeroData
from .migrate import async_migrate_entry as async_migrate_entry
from .platform_helpers import async_setup_account_coordinators, get_update_interval

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import device_registry as dr

    from .data import OgeroConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: OgeroConfigEntry) -> bool:
    """Set up Ogero from a config entry."""
    client = create_api_client(
        hass,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    entry.runtime_data = OgeroData(
        client=client,
        integration=async_get_loaded_integration(hass, entry.domain),
    )
    entry.runtime_data.coordinators.clear()
    await async_setup_account_coordinators(hass, entry, get_update_interval(entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OgeroConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data = None
    return bool(unloaded)


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: OgeroConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Remove a device by removing its config subentry."""
    for identifier in device.identifiers:
        if identifier[0] != DOMAIN:
            continue
        subentry_id = identifier[1]
        if subentry_id in entry.subentries:
            hass.config_entries.async_remove_subentry(entry, subentry_id)
            return True
    return False
