"""Binary sensor platform for ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import SUBENTRY_TYPE_ACCOUNT
from .entity import OgeroEntity

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import OgeroDataUpdateCoordinator
    from .data import OgeroConfigEntry

UNPAID_BILLS = "unpaid_bills"
OVER_QUOTA = "over_quota"

BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=UNPAID_BILLS,
        translation_key=UNPAID_BILLS,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    BinarySensorEntityDescription(
        key=OVER_QUOTA,
        translation_key=OVER_QUOTA,
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: OgeroConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Ogero binary sensors."""
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_ACCOUNT:
            continue
        coordinator = entry.runtime_data.coordinators.get(subentry.subentry_id)
        if coordinator is None:
            continue
        async_add_entities(
            [
                OgeroBinarySensor(coordinator, subentry, entity_description)
                for entity_description in BINARY_SENSOR_DESCRIPTIONS
            ],
            config_subentry_id=subentry.subentry_id,
        )


class OgeroBinarySensor(
    OgeroEntity,
    BinarySensorEntity,  # type: ignore[misc]
):
    """Ogero binary sensor."""

    entity_description: BinarySensorEntityDescription

    def __init__(
        self,
        coordinator: OgeroDataUpdateCoordinator,
        subentry: ConfigSubentry,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, subentry, entity_description.key)
        self.entity_description = entity_description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        data = self.coordinator.data
        if data is None:
            return None
        if self.entity_description.key == UNPAID_BILLS:
            return bool(data.has_unpaid_bills)
        if self.entity_description.key == OVER_QUOTA:
            return bool(data.has_extra_consumption)
        return None
