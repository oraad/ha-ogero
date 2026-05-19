"""Tests for Ogero API client helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from custom_components.ogero.api import create_api_client

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_create_api_client_injects_websession(hass: HomeAssistant) -> None:
    """create_api_client uses Home Assistant shared aiohttp session."""
    mock_session = MagicMock()
    with patch(
        "custom_components.ogero.api.async_get_clientsession",
        return_value=mock_session,
    ) as get_session:
        client = create_api_client(hass, "user", "pass")

    get_session.assert_called_once_with(hass)
    assert client.ogero_client.session is mock_session
