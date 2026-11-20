"""Config flow tests."""

from unittest.mock import AsyncMock

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.bin_collection_toowoomba_qld.api import AddressNotFound, CannotConnect
from custom_components.bin_collection_toowoomba_qld.const import (
    CONF_ADDRESS,
    CONF_GREEN_SERVICE,
    DOMAIN,
)

from .conftest import ADDRESS


async def test_full_flow(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"search": "3 Parsons"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select"
    mock_api.search_addresses.assert_awaited_once_with("3 Parsons")

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == ADDRESS
    assert result["data"] == {CONF_ADDRESS: ADDRESS, CONF_GREEN_SERVICE: True}
    assert result["result"].unique_id == ADDRESS.lower()


async def test_search_too_short(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"search": "3 P"})
    assert result["errors"] == {"search": "too_short"}
    mock_api.search_addresses.assert_not_awaited()


async def test_search_no_results(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    mock_api.search_addresses.return_value = []
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"search": "Nowhere"}
    )
    assert result["errors"] == {"search": "no_results"}


async def test_search_cannot_connect(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    mock_api.search_addresses.side_effect = CannotConnect
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"search": "3 Parsons"}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_select_no_collection_then_recover(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    mock_api.get_collection.side_effect = AddressNotFound
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"search": "3 Parsons"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["step_id"] == "select"
    assert result["errors"] == {"base": "no_collection"}

    mock_api.get_collection.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_already_configured(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    MockConfigEntry(
        domain=DOMAIN, unique_id=ADDRESS.lower(), data={CONF_ADDRESS: ADDRESS}
    ).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"search": "3 Parsons"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ADDRESS: ADDRESS}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
