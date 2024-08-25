"""Sensor platform for ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.sensor.const import SensorDeviceClass

from .const import DOMAIN, LOGGER
from .entity import OgeroEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import OgeroDataUpdateCoordinator

SPEED = "speed"
# UPLOAD = "upload"
# DOWNLOAD = "download"
TOTAL_CONSUMPTION = "total_consumption"
EXTRA_CONSUMPTION = "extra_consumption"
QUOTA = "quota"
LAST_UPDATE = "last_update"

OUTSTANDING_BALANCE = "outstanding_balance"

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key=QUOTA,
        translation_key=QUOTA,
        native_unit_of_measurement="GB",
        suggested_display_precision=0,
        icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=SPEED,
        translation_key=SPEED,
        icon="mdi:speedometer",
    ),
    # SensorEntityDescription(
    #     key=DOWNLOAD,
    #     translation_key=DOWNLOAD,
    #     native_unit_of_measurement="GB",
    #     suggested_display_precision=1,
    #     icon="mdi:download",
    # ),
    # SensorEntityDescription(
    #     key=UPLOAD,
    #     translation_key=UPLOAD,
    #     native_unit_of_measurement="GB",
    #     suggested_display_precision=1,
    #     icon="mdi:upload",
    # ),
    SensorEntityDescription(
        key=TOTAL_CONSUMPTION,
        translation_key=TOTAL_CONSUMPTION,
        native_unit_of_measurement="GB",
        suggested_display_precision=1,
        icon="mdi:sigma",
    ),
    SensorEntityDescription(
        key=EXTRA_CONSUMPTION,
        translation_key=EXTRA_CONSUMPTION,
        native_unit_of_measurement="GB",
        suggested_display_precision=1,
        icon="mdi:alert",
    ),
    SensorEntityDescription(
        key=LAST_UPDATE,
        translation_key=LAST_UPDATE,
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:update",
    ),
)

EXTENDED_ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key=OUTSTANDING_BALANCE,
        translation_key=OUTSTANDING_BALANCE,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="LBP",
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: AddEntitiesCallback
):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        OgeroSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

    async_add_devices(
        ExtendedOgeroSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in EXTENDED_ENTITY_DESCRIPTIONS
    )


class OgeroSensor(OgeroEntity, SensorEntity):
    """ogero Sensor class."""

    def __init__(
        self,
        coordinator: OgeroDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator, entity_description.key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)


class ExtendedOgeroSensor(OgeroSensor):
    _attr_extra_state_attributes: ClassVar[dict] = {}

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        attributes = self.coordinator.data.get("state_attributes").get(
            self.entity_description.key
        )

        if attributes is not None:
            for attribute in attributes:
                key, value = attribute
                LOGGER.debug("attribute key: %s, value: %s", key, value)
                self._attr_extra_state_attributes[key] = value

        return self.coordinator.data.get(self.entity_description.key)
