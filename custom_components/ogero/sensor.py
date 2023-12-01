"""Sensor platform for ogero."""
from __future__ import annotations

from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
)

from .const import DOMAIN, LOGGER
from .coordinator import OgeroDataUpdateCoordinator
from .entity import OgeroEntity

SPEED = "speed"
UPLOAD = "upload"
DOWNLOAD = "download"
TOTAL_CONSUMPTION = "total_consumption"
EXTRA_CONSUMPTION = "extra_consumption"
QUOTA = "quota"
LAST_UPDATE = "last_update"

OUTSTANDING_BALANCE = "outstanding_balance"

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key=QUOTA,
        name=QUOTA,
        native_unit_of_measurement="GB",
        suggested_display_precision=0
        # icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=SPEED,
        name=SPEED,
        # device_class=SensorDeviceClass
        # icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=DOWNLOAD,
        name=DOWNLOAD,
        native_unit_of_measurement="GB",
        suggested_display_precision=1
        # icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=UPLOAD,
        name=UPLOAD,
        native_unit_of_measurement="GB",
        suggested_display_precision=1
        # icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=TOTAL_CONSUMPTION,
        name=TOTAL_CONSUMPTION,
        native_unit_of_measurement="GB",
        suggested_display_precision=1
        # icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=EXTRA_CONSUMPTION,
        name=EXTRA_CONSUMPTION,
        native_unit_of_measurement="GB",
        suggested_display_precision=1
        # icon="mdi:format-quote-close",
    ),
    SensorEntityDescription(
        key=LAST_UPDATE, name=LAST_UPDATE, device_class=SensorDeviceClass.TIMESTAMP
    ),
)

EXTENDED_ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key=OUTSTANDING_BALANCE,
        name=OUTSTANDING_BALANCE,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="LBP",
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
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.get(self.entity_description.key)


class ExtendedOgeroSensor(OgeroSensor):
    _attr_extra_state_attributes = {}

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        attributes = self.coordinator.data.get("state_attributes").get(
            self.entity_description.key
        )

        for attribute in attributes:
            key, value = attribute
            LOGGER.debug("attribute key: %s, value: %s", key, value)
            self._attr_extra_state_attributes[key] = value

        return self.coordinator.data.get(self.entity_description.key)

    # async def async_update(self):
    #     attributes = self.coordinator.data.get("state_attributes").get(
    #         self.entity_description.key
    #     )

    #     for attribute in attributes:
    #         key, value = attribute
    #         LOGGER.debug("attribute key: %s, value: %s", key, value)
    #         self._attr_extra_state_attributes[key] = value
