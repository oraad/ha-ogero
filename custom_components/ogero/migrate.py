"""Config entry migration."""

from __future__ import annotations

from copy import deepcopy
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .const import CONF_ACCOUNT, CONFIG_ENTRY_VERSION, DOMAIN, LOGGER, SUBENTRY_TYPE_ACCOUNT

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import OgeroConfigEntry


def _username_unique_id(username: str) -> str:
    """Return a stable unique id for an Ogero login."""
    return cast("str", slugify(username))


def _is_parent_ogero_entry(other: OgeroConfigEntry, username_unique_id: str) -> bool:
    """True if this config entry is a parent login (v2/v3), not a v1 row."""
    return (
        other.domain == DOMAIN
        and other.unique_id == username_unique_id
        and CONF_USERNAME in other.data
        and CONF_ACCOUNT not in other.data
    )


def _find_parent_entry(
    hass: HomeAssistant, username_unique_id: str, exclude_entry_id: str
) -> OgeroConfigEntry | None:
    """Return an existing parent entry for this login, if any."""
    for other in hass.config_entries.async_entries(DOMAIN):
        if other.entry_id == exclude_entry_id:
            continue
        if _is_parent_ogero_entry(other, username_unique_id):
            return other
    return None


def _rehome_entities_v2_to_v3(
    hass: HomeAssistant,
    entry_id: str,
    subentry_id_to_serial: dict[str, str],
) -> None:
    """Rewrite entity unique_ids from subentry ULID to account serial."""
    entity_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_reg, entry_id):
        if not entity.unique_id:
            continue
        for sub_id, serial in subentry_id_to_serial.items():
            if not entity.unique_id.startswith(f"{sub_id}_"):
                continue
            suffix = entity.unique_id[len(sub_id) + 1 :]
            entity_reg.async_update_entity(
                entity.entity_id,
                new_unique_id=f"{serial}_{suffix}",
                config_subentry_id=None,
            )
            break


def _rehome_devices_v2_to_v3(
    hass: HomeAssistant,
    entry_id: str,
    subentry_id_to_serial: dict[str, str],
) -> None:
    """Rewrite device identifiers from subentry id to account serial."""
    device_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_reg, entry_id):
        new_identifiers = deepcopy(device.identifiers)
        for sub_id, serial in subentry_id_to_serial.items():
            if (DOMAIN, sub_id) in new_identifiers:
                new_identifiers.discard((DOMAIN, sub_id))
                new_identifiers.add((DOMAIN, serial))
                device_reg.async_update_device(
                    device.id,
                    new_identifiers=new_identifiers,
                    remove_config_subentry_id=sub_id,
                )
                break


def _rehome_entities_v1_to_v3(
    hass: HomeAssistant,
    source_entry_id: str,
    target_entry_id: str,
    account_serial: str,
    old_id_prefix: str,
) -> None:
    """Map v1-style entity unique_ids to account_serial_* on target entry."""
    entity_reg = er.async_get(hass)
    for entity in er.async_entries_for_config_entry(entity_reg, source_entry_id):
        if not entity.unique_id:
            continue
        uid = entity.unique_id
        new_unique_id: str | None = None
        if uid.startswith(f"{account_serial}_"):
            new_unique_id = uid
        elif uid.startswith(f"{old_id_prefix}_"):
            suffix = uid[len(old_id_prefix) + 1 :]
            new_unique_id = f"{account_serial}_{suffix}"
        if new_unique_id is None:
            LOGGER.warning(
                "Skipping entity %s with unexpected unique_id %s during migration",
                entity.entity_id,
                entity.unique_id,
            )
            continue
        entity_reg.async_update_entity(
            entity.entity_id,
            config_entry_id=target_entry_id,
            new_unique_id=new_unique_id,
            config_subentry_id=None,
        )


def _rehome_devices_v1_to_v3(
    hass: HomeAssistant,
    source_entry_id: str,
    target_entry_id: str,
    account_serial: str,
) -> None:
    """Move devices from a v1 child entry onto the parent using account serial."""
    device_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_reg, source_entry_id):
        new_identifiers = deepcopy(device.identifiers)
        changed = False
        for identifier in list(new_identifiers):
            domain, value = identifier
            if domain != DOMAIN:
                continue
            if value in {source_entry_id, account_serial}:
                new_identifiers.discard(identifier)
                new_identifiers.add((DOMAIN, account_serial))
                changed = True
        if not changed:
            continue
        device_reg.async_update_device(
            device.id,
            new_identifiers=new_identifiers,
            add_config_entry_id=target_entry_id,
        )
        device_reg.async_update_device(
            device.id,
            remove_config_entry_id=source_entry_id,
        )


async def _migrate_v1_to_v3(hass: HomeAssistant, entry: OgeroConfigEntry) -> None:
    """Migrate a v1 entry to v3 (credentials only, no subentries)."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    account_serial = entry.data[CONF_ACCOUNT]
    username_unique_id = _username_unique_id(username)

    parent_entry = _find_parent_entry(hass, username_unique_id, entry.entry_id)

    if parent_entry is not None:
        _rehome_entities_v1_to_v3(
            hass,
            entry.entry_id,
            parent_entry.entry_id,
            account_serial,
            entry.entry_id,
        )
        _rehome_devices_v1_to_v3(
            hass,
            entry.entry_id,
            parent_entry.entry_id,
            account_serial,
        )
        hass.async_create_task(hass.config_entries.async_remove(entry.entry_id))
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
    _rehome_entities_v1_to_v3(
        hass,
        entry.entry_id,
        entry.entry_id,
        account_serial,
        entry.entry_id,
    )
    _rehome_devices_v1_to_v3(hass, entry.entry_id, entry.entry_id, account_serial)


async def _migrate_v2_to_v3(hass: HomeAssistant, entry: OgeroConfigEntry) -> None:
    """Migrate v2 subentries to v3 (API-driven accounts, no subentries)."""
    subentry_id_to_serial: dict[str, str] = {}
    for sub in entry.subentries.values():
        if sub.subentry_type != SUBENTRY_TYPE_ACCOUNT:
            continue
        serial = cast("str", sub.data.get(CONF_ACCOUNT) or sub.unique_id or "")
        if not serial:
            continue
        subentry_id_to_serial[sub.subentry_id] = serial

    if subentry_id_to_serial:
        _rehome_entities_v2_to_v3(hass, entry.entry_id, subentry_id_to_serial)
        _rehome_devices_v2_to_v3(hass, entry.entry_id, subentry_id_to_serial)

    hass.config_entries.async_update_entry(
        entry,
        version=CONFIG_ENTRY_VERSION,
        subentries=MappingProxyType({}),
    )


async def async_migrate_entry(hass: HomeAssistant, entry: OgeroConfigEntry) -> bool:
    """Migrate old config entries."""
    if entry.version > CONFIG_ENTRY_VERSION:
        return False

    if entry.version == 1:
        await _migrate_v1_to_v3(hass, entry)
    elif entry.version == 2:
        await _migrate_v2_to_v3(hass, entry)

    return True
