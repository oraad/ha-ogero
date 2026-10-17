"""Sensor platform for ogero."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.helpers.entity import EntityCategory

from .const import UNLIMITED_QUOTA
from .entity import OgeroEntity

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .api import Account
    from .coordinator import OgeroDataUpdateCoordinator
    from .data import OgeroConfigEntry

OgeroSensorValue = int | float | str | datetime | None

SPEED = "speed"
TOTAL_CONSUMPTION = "total_consumption"
EXTRA_CONSUMPTION = "extra_consumption"
QUOTA = "quota"
USAGE = "usage"
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
        key=USAGE,
        translation_key=USAGE,
        native_unit_of_measurement="%",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key=SPEED,
        translation_key=SPEED,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
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
    for coordinator in entry.runtime_data.coordinators.values():
        async_add_entities(
            [
                OgeroSensor(coordinator, coordinator.account, entity_description)
                for entity_description in ENTITY_DESCRIPTIONS
            ],
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
        account: Account,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, account, entity_description.key)
        self.entity_description = entity_description

    @property
    def native_value(self) -> OgeroSensorValue:
        """Return the native value of the sensor."""
        data = self.coordinator.data
        if data is None:
            return None
        return cast("OgeroSensorValue", getattr(data, self.entity_description.key))

    @property
    def _is_unlimited_quota(self) -> bool:
        """Return True for the quota sensor when the plan is unlimited."""
        return (
            self.entity_description.key == QUOTA
            and self.coordinator.data is not None
            and self.coordinator.data.quota == UNLIMITED_QUOTA
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Drop the GB unit when the quota is unlimited."""
        if self._is_unlimited_quota:
            return None
        return cast("str | None", self.entity_description.native_unit_of_measurement)

    @property
    def suggested_display_precision(self) -> int | None:
        """
        Drop display precision when the quota is unlimited.

        Home Assistant requires a numeric state whenever a unit or display
        precision is set, so both must be cleared to expose the "Unlimited"
        text state.
        """
        if self._is_unlimited_quota:
            return None
        return cast("int | None", self.entity_description.suggested_display_precision)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        data = self.coordinator.data
        if data is None:
            return None
        if self.entity_description.key == OUTSTANDING_BALANCE and data.unpaid_bills:
            return {"unpaid_bills": data.unpaid_bills}
        if self.entity_description.key == USAGE:
            return {"quota_is_unlimited": data.quota == UNLIMITED_QUOTA}
        return None
