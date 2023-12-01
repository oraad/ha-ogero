"""Library for extracting device specific information common to entities."""

from __future__ import annotations
from typing import Optional

from homeassistant.const import CONF_NAME
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType

from .const import DOMAIN, NAME, VERSION


class OgeroDeviceInfo:
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        name: str,
        device_type: Optional[DeviceEntryType] = None,
    ) -> None:
        """Initialize the DeviceInfo."""
        self._hass = hass
        self._config_entry = config_entry
        self._device_type = device_type
        self._name = name

    @property
    def available(self) -> bool:
        """Return device availability."""
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""

        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name=self._name,
            model=VERSION,
            manufacturer=NAME,
            entry_type=self._device_type,
        )

    @property
    def device_id(self):
        device_info = self.device_info
        device_registry = dr.async_get(self._hass)
        if device_entry := device_registry.async_get_device(
            identifiers=device_info["identifiers"]
        ):
            return device_entry.id
