"""Config entry migration."""

from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util.slugify import slugify

from .api import Account
from .const import (
    CONF_ACCOUNT,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
    LOGGER,
    SUBENTRY_TYPE_ACCOUNT,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import OgeroConfigEntry


def _username_unique_id(username: str) -> str:
    """Return a stable unique id for an Ogero login."""
    return slugify(username)


def _find_parent_entry(
    hass: HomeAssistant, username_unique_id: str, exclude_entry_id: str
) -> OgeroConfigEntry | None:
    """Return an existing v2 parent entry for this login, if any."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == exclude_entry_id:
            continue
        if (
            other.version >= CONFIG_ENTRY_VERSION
            and other.unique_id == username_unique_id
        ):
            return other
    return None


def _get_subentry_id_for_account(
    entry: OgeroConfigEntry, account_serial: str
) -> str | None:
    """Return subentry id for an account serial on this entry."""
    for subentry in entry.subentries.values():
        if (
            subentry.subentry_type == SUBENTRY_TYPE_ACCOUNT
            and subentry.unique_id == account_serial
        ):
            return subentry.subentry_id
    return None


def _add_account_subentry(
    hass: HomeAssistant,
    entry: OgeroConfigEntry,
    account_serial: str,
) -> str:
    """Add an account subentry and return its id."""
    existing_id = _get_subentry_id_for_account(entry, account_serial)
    if existing_id:
        LOGGER.warning(
            "Account %s already configured on entry %s during migration",
            account_serial,
            entry.entry_id,
        )
        return existing_id

    account = Account.deserialize(account_serial)
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ACCOUNT: account_serial}),
        subentry_type=SUBENTRY_TYPE_ACCOUNT,
        title=str(account),
        unique_id=account_serial,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry.subentry_id


def _rehome_entities(
    hass: HomeAssistant,
    old_entry_id: str,
    new_entry_id: str,
    account_serial: str,
    subentry_id: str,
) -> None:
    """Move entity registry entries to the parent entry and subentry."""
    entity_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_reg, old_entry_id):
        if not entity.unique_id:
            continue

        new_unique_id: str | None = None
        if entity.unique_id.startswith(f"{account_serial}_"):
            suffix = entity.unique_id[len(account_serial) + 1 :]
            new_unique_id = f"{subentry_id}_{suffix}"
        elif entity.unique_id.startswith(f"{old_entry_id}_"):
            suffix = entity.unique_id[len(old_entry_id) + 1 :]
            new_unique_id = f"{subentry_id}_{suffix}"

        if new_unique_id is None:
            LOGGER.warning(
                "Skipping entity %s with unexpected unique_id %s during migration",
                entity.entity_id,
                entity.unique_id,
            )
            continue

        entity_reg.async_update_entity(
            entity.entity_id,
            config_entry_id=new_entry_id,
            config_subentry_id=subentry_id,
            new_unique_id=new_unique_id,
        )


def _rehome_devices(
    hass: HomeAssistant,
    old_entry_id: str,
    new_entry_id: str,
    account_serial: str,
    subentry_id: str,
) -> None:
    """Update device identifiers and subentry association."""
    device_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_reg, old_entry_id):
        new_identifiers = deepcopy(device.identifiers)
        updated = False
        for identifier in list(new_identifiers):
            domain, value = identifier
            if domain != DOMAIN:
                continue
            if value in {old_entry_id, account_serial}:
                new_identifiers.discard(identifier)
                new_identifiers.add((DOMAIN, subentry_id))
                updated = True

        if not updated:
            continue

        device_reg.async_update_device(
            device.id,
            new_identifiers=new_identifiers,
            add_config_entry_id=new_entry_id,
            add_config_subentry_id=subentry_id,
        )
        device_reg.async_update_device(
            device.id,
            remove_config_entry_id=new_entry_id,
            remove_config_subentry_id=None,
        )


async def _migrate_v1_to_v2(hass: HomeAssistant, entry: OgeroConfigEntry) -> None:
    """Migrate a v1 entry to v2 parent + account subentry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    account_serial = entry.data[CONF_ACCOUNT]
    username_unique_id = _username_unique_id(username)

    parent_entry = _find_parent_entry(hass, username_unique_id, entry.entry_id)

    if parent_entry is not None:
        subentry_id = _add_account_subentry(hass, parent_entry, account_serial)
        _rehome_entities(
            hass,
            entry.entry_id,
            parent_entry.entry_id,
            account_serial,
            subentry_id,
        )
        _rehome_devices(
            hass,
            entry.entry_id,
            parent_entry.entry_id,
            account_serial,
            subentry_id,
        )
        hass.config_entries.async_remove(entry.entry_id)
        return

    hass.config_entries.async_update_entry(
        entry,
        version=CONFIG_ENTRY_VERSION,
        unique_id=username_unique_id,
        title=username,
        data={
            CONF_USERNAME: username,
            CONF_PASSWORD: password,
        },
    )
    subentry_id = _add_account_subentry(hass, entry, account_serial)
    _rehome_entities(hass, entry.entry_id, entry.entry_id, account_serial, subentry_id)
    _rehome_devices(hass, entry.entry_id, entry.entry_id, account_serial, subentry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: OgeroConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version > CONFIG_ENTRY_VERSION:
        return False

    if entry.version == 1:
        await _migrate_v1_to_v2(hass, entry)

    return True
