"""OgeroEntity class."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, NAME, VERSION
from .coordinator import OgeroDataUpdateCoordinator


class OgeroEntity(CoordinatorEntity[OgeroDataUpdateCoordinator]):
    """OgeroEntity class."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, coordinator: OgeroDataUpdateCoordinator, name: str) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = coordinator.config_entry.entry_id + "_" + name
        self._attr_device_info = coordinator.device.device_info
