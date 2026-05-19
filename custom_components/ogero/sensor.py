"""Sensor platform for ogero."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from .const import SUBENTRY_TYPE_ACCOUNT
from .entity import OgeroEntity

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import OgeroDataUpdateCoordinator
    from .data import OgeroConfigEntry

OgeroSensorValue = int | float | str | datetime | None

SPEED = "speed"
UPLOAD = "upload"
DOWNLOAD = "download"
TOTAL_CONSUMPTION = "total_consumption"
EXTRA_CONSUMPTION = "extra_consumption"
QUOTA = "quota"
LAST_UPDATE = "last_update"
OUTSTANDING_BALANCE = "outstanding_balance"

ENTITY_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=QUOTA,
        translation_key=QUOTA,
        native_unit_of_measurement="GB",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key=SPEED,
        translation_key=SPEED,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=UPLOAD,
        translation_key=UPLOAD,
        native_unit_of_measurement="GB",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=DOWNLOAD,
        translation_key=DOWNLOAD,
        native_unit_of_measurement="GB",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=TOTAL_CONSUMPTION,
        translation_key=TOTAL_CONSUMPTION,
        native_unit_of_measurement="GB",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=EXTRA_CONSUMPTION,
        translation_key=EXTRA_CONSUMPTION,
        native_unit_of_measurement="GB",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=LAST_UPDATE,
        translation_key=LAST_UPDATE,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=OUTSTANDING_BALANCE,
        translation_key=OUTSTANDING_BALANCE,
        device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="LBP",
        suggested_display_precision=0,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: OgeroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ogero sensors."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_ACCOUNT:
            continue
        coordinator = entry.runtime_data.coordinators.get(subentry.subentry_id)
        if coordinator is None:
            continue
        async_add_entities(
            [
                OgeroSensor(coordinator, subentry, entity_description)
                for entity_description in ENTITY_DESCRIPTIONS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class OgeroSensor(
    OgeroEntity,
    SensorEntity,  # type: ignore[misc]
):
    """Ogero sensor."""

    entity_description: SensorEntityDescription

    def __init__(
        self,
        coordinator: OgeroDataUpdateCoordinator,
        subentry: ConfigSubentry,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, subentry, entity_description.key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> OgeroSensorValue:
        """Return the native value of the sensor."""
        data = self.coordinator.data
        if data is None:
            return None
        return cast("OgeroSensorValue", getattr(data, self.entity_description.key))

    @property
    def extra_state_attributes(self) -> dict[str, list[dict[str, str]]] | None:
        """Return extra state attributes."""
        if self.entity_description.key != OUTSTANDING_BALANCE:
            return None
        data = self.coordinator.data
        if data is None or not data.unpaid_bills:
            return None
        return {"unpaid_bills": data.unpaid_bills}
