"""Diagnostics support for Ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import DOMAIN, VERSION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import OgeroCoordinatorData
    from .data import OgeroConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
}


class OgeroAccountDiagnostics(TypedDict, total=False):
    """Diagnostics payload for one account line."""

    account_serial: str
    last_update_success: bool | None
    last_exception: str | None
    data: dict[str, object] | None


class OgeroDiagnosticsPayload(TypedDict):
    """Diagnostics payload for the integration."""

    domain: str
    integration_version: str
    options: dict[str, object]
    accounts: list[OgeroAccountDiagnostics]


def _coordinator_data_dict(data: OgeroCoordinatorData) -> dict[str, object]:
    return {
        "quota": data.quota,
        "speed": data.speed,
        "total_consumption": data.total_consumption,
        "extra_consumption": data.extra_consumption,
        "last_update": data.last_update,
        "outstanding_balance": data.outstanding_balance,
        "unpaid_bills": data.unpaid_bills,
        "has_unpaid_bills": data.has_unpaid_bills,
        "has_extra_consumption": data.has_extra_consumption,
    }


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: OgeroConfigEntry
) -> OgeroDiagnosticsPayload:
    """Return diagnostics for a config entry."""
    runtime = entry.runtime_data
    accounts: list[OgeroAccountDiagnostics] = []

    for account_key, coordinator in runtime.coordinators.items():
        accounts.append(
            {
                "account_serial": account_key,
                "last_update_success": coordinator.last_update_success,
                "last_exception": repr(coordinator.last_exception)
                if coordinator.last_exception
                else None,
                "data": _coordinator_data_dict(coordinator.data)
                if coordinator.data
                else None,
            }
        )

    return cast(
        "OgeroDiagnosticsPayload",
        async_redact_data(
            {
                "domain": DOMAIN,
                "integration_version": VERSION,
                "options": dict(entry.options),
                "accounts": accounts,
            },
            TO_REDACT,
        ),
    )
