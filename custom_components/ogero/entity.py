"""OgeroEntity class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION
from .coordinator import OgeroDataUpdateCoordinator

if TYPE_CHECKING:
    from .api import Account


class OgeroEntity(CoordinatorEntity[OgeroDataUpdateCoordinator]):  # type: ignore[misc]
    """Base entity for Ogero."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OgeroDataUpdateCoordinator,
        account: Account,
        key: str,
    ) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._key = key
        self._account = account
        serial = account.serial
        self._attr_unique_id = f"{serial}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            name=str(account),
            manufacturer=NAME,
            model=serial,
        )

    @property
    def available(self) -> bool:
        """Show last successful snapshot when a poll fails (UpdateFailed)."""
        return self.coordinator.data is not None
