"""Custom types for the Ogero integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.loader import Integration

    from .api import OgeroApiClient
    from .coordinator import OgeroDataUpdateCoordinator


type OgeroConfigEntry = ConfigEntry[OgeroData]


@dataclass
class OgeroData:
    """Runtime data for an Ogero config entry."""

    client: OgeroApiClient
    integration: Integration
    coordinators: dict[str, OgeroDataUpdateCoordinator] = field(default_factory=dict)
