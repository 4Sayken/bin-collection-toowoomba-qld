"""Setup and entity tests."""

from datetime import date
from unittest.mock import AsyncMock

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.bin_collection_toowoomba_qld.api import BinCollection, CannotConnect
from custom_components.bin_collection_toowoomba_qld.const import (
    CONF_ADDRESS,
    CONF_GREEN_SERVICE,
    DOMAIN,
)

from .conftest import ADDRESS

PREFIX = "3_parsons_street_rangeville_qld_4350"


def _entry(hass: HomeAssistant, green: bool = True) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=ADDRESS,
        unique_id=ADDRESS.lower(),
        data={CONF_ADDRESS: ADDRESS, CONF_GREEN_SERVICE: green},
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.freeze_time("2026-11-16 19:00:00+10:00")
async def test_entities_on_bin_night(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    await hass.config.async_set_time_zone("Australia/Brisbane")
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    assert hass.states.get(f"sensor.{PREFIX}_next_collection").state == "2026-11-17"
    assert (
        hass.states.get(f"sensor.{PREFIX}_bins_to_put_out").state == "General waste & Green waste"
    )
    assert hass.states.get(f"sensor.{PREFIX}_days_until_collection").state == "1"
    assert hass.states.get(f"binary_sensor.{PREFIX}_green_waste_week").state == "on"
    assert hass.states.get(f"binary_sensor.{PREFIX}_recycling_week").state == "off"
    assert hass.states.get(f"binary_sensor.{PREFIX}_bin_night").state == "on"

    attrs = hass.states.get(f"sensor.{PREFIX}_next_collection").attributes
    assert attrs["estimated"] is False
    assert attrs["bins"] == ["General waste", "Green waste"]

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED


@pytest.mark.freeze_time("2026-11-20 12:00:00+10:00")
async def test_rolls_forward_after_collection(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    await hass.config.async_set_time_zone("Australia/Brisbane")
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get(f"sensor.{PREFIX}_next_collection").state == "2026-11-24"
    assert hass.states.get(f"sensor.{PREFIX}_bins_to_put_out").state == "General waste & Recycling"
    assert hass.states.get(f"binary_sensor.{PREFIX}_bin_night").state == "off"
    assert hass.states.get(f"sensor.{PREFIX}_next_collection").attributes["estimated"] is True
    assert hass.states.get(f"sensor.{PREFIX}_next_recycling").state == "2026-11-24"
    assert hass.states.get(f"sensor.{PREFIX}_next_green_waste").state == "2026-12-01"


@pytest.mark.freeze_time("2026-11-23 00:00:30+10:00")
async def test_midnight_refresh_turns_on_bin_night(
    hass: HomeAssistant, mock_api: AsyncMock, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("Australia/Brisbane")
    mock_api.get_collection.return_value = BinCollection(
        address=ADDRESS,
        description="General & Recycle",
        collection_date=date(2026, 11, 24),
        image_url=None,
    )
    entry = _entry(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(f"binary_sensor.{PREFIX}_bin_night").state == "on"
    calls = mock_api.get_collection.await_count

    # Just after midnight on collection day: refreshed, and bin night is over.
    freezer.move_to("2026-11-24 00:01:00+10:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert mock_api.get_collection.await_count > calls
    assert hass.states.get(f"binary_sensor.{PREFIX}_bin_night").state == "off"


async def test_learns_green_service(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    entry = _entry(hass, green=False)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.data[CONF_GREEN_SERVICE] is True


async def test_setup_retry_when_offline(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    mock_api.get_collection.side_effect = CannotConnect
    entry = _entry(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY
