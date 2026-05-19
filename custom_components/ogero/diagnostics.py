"""Diagnostics support for Ogero."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict, cast

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from .const import CONF_ACCOUNT, DOMAIN, SUBENTRY_TYPE_ACCOUNT, VERSION

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import OgeroCoordinatorData
    from .data import OgeroConfigEntry

TO_REDACT = {
    CONF_PASSWORD,
    CONF_USERNAME,
}


class OgeroAccountDiagnostics(TypedDict, total=False):
    """Diagnostics payload for one account subentry."""

    subentry_id: str
    account: str | None
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
        "upload": data.upload,
        "download": data.download,
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

    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TYPE_ACCOUNT:
            continue
        coordinator = runtime.coordinators.get(subentry.subentry_id)
        accounts.append(
            {
                "subentry_id": subentry.subentry_id,
                "account": subentry.data.get(CONF_ACCOUNT),
                "last_update_success": coordinator.last_update_success
                if coordinator
                else None,
                "last_exception": repr(coordinator.last_exception)
                if coordinator and coordinator.last_exception
                else None,
                "data": _coordinator_data_dict(coordinator.data)
                if coordinator and coordinator.data
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
