"""OgeroEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Account
from .const import ATTRIBUTION, CONF_ACCOUNT, DOMAIN, NAME, VERSION
from .coordinator import OgeroDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry


class OgeroEntity(CoordinatorEntity[OgeroDataUpdateCoordinator]):  # type: ignore[misc]
    """Base entity for Ogero."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OgeroDataUpdateCoordinator,
        subentry: ConfigSubentry,
        key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._key = key
        self._subentry = subentry
        self._attr_unique_id = f"{subentry.subentry_id}_{key}"
        account = Account.deserialize(subentry.data[CONF_ACCOUNT])
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=str(account),
            manufacturer=NAME,
            model=VERSION,
        )
