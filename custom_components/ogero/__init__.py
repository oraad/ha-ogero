"""
Custom integration to integrate Ogero Telekom with Home Assistant.

For more details about this integration, please refer to
https://github.com/oraad/ha-ogero
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyogero.asyncio import AuthenticationException

from .api import (
    Account,
    OgeroApiClient,
    OgeroApiClientAuthenticationError,
    OgeroApiClientCommunicationError,
    OgeroApiClientError,
)
from .const import DOMAIN
from .coordinator import OgeroDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [Platform.SENSOR]

ACCOUNT = "account"


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    if CONF_USERNAME not in entry.data:
        raise ConfigEntryAuthFailed

    try:
        client = OgeroApiClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            session=async_get_clientsession(hass),
        )
        await client.async_login()
    except AuthenticationException as exception:
        raise ConfigEntryAuthFailed from exception
    except OgeroApiClientAuthenticationError as exception:
        raise ConfigEntryAuthFailed from exception
    except OgeroApiClientCommunicationError as exception:
        raise ConfigEntryNotReady from exception
    except OgeroApiClientError as exception:
        raise ConfigEntryNotReady from exception

    if ACCOUNT not in entry.data:
        raise ConfigEntryAuthFailed

    account = Account.deserialize(entry.data[ACCOUNT])

    hass.data[DOMAIN][entry.entry_id] = coordinator = OgeroDataUpdateCoordinator(
        hass=hass,
        account=account,
        client=client,
    )
    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
