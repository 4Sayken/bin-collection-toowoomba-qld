"""Tests for the monthly check, the saved reading and the check-for-changes button."""

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, patch
import zlib

from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.bin_collection_toowoomba_qld.api import BinCollection, CannotConnect
from custom_components.bin_collection_toowoomba_qld.const import (
    CHECK_HOUR,
    CONF_ADDRESS,
    CONF_GREEN_SERVICE,
    DOMAIN,
)

from .conftest import ADDRESS

PREFIX = "3_parsons_street_rangeville_qld_4350"
BUTTON = f"button.{PREFIX}_check_for_changes"
NOTIFY = "custom_components.bin_collection_toowoomba_qld.coordinator.persistent_notification"

RECYCLE_WEEK = BinCollection(
    address=ADDRESS,
    description="General & Recycle",
    collection_date=date(2026, 11, 17),
    image_url=None,
)


def _entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=ADDRESS,
        unique_id=ADDRESS.lower(),
        data={CONF_ADDRESS: ADDRESS, CONF_GREEN_SERVICE: True},
    )
    entry.add_to_hass(hass)
    return entry


def _save_reading(hass_storage: dict[str, Any], entry: MockConfigEntry, last_checked: str) -> None:
    """Pretend an earlier check saved a green-waste week reading."""
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {
        "version": 1,
        "minor_version": 1,
        "key": f"{DOMAIN}.{entry.entry_id}",
        "data": {
            "collection": {
                "address": ADDRESS,
                "description": "General & Greenwaste",
                "collection_date": "2026-11-17",
                "image_url": None,
            },
            "last_checked": last_checked,
            "last_changed": last_checked,
        },
    }


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config.async_set_time_zone("Australia/Brisbane")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.freeze_time("2026-11-20 12:00:00+10:00")
async def test_first_setup_checks_and_saves(
    hass: HomeAssistant, mock_api: AsyncMock, hass_storage: dict[str, Any]
) -> None:
    entry = _entry(hass)
    await _setup(hass, entry)
    assert mock_api.get_collection.await_count == 1

    saved = hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]
    assert saved["collection"]["collection_date"] == "2026-11-17"
    assert hass.states.get(f"sensor.{PREFIX}_last_checked").state == "2026-11-20T02:00:00+00:00"
    assert hass.states.get(f"sensor.{PREFIX}_last_changed").state == "2026-11-20T02:00:00+00:00"


@pytest.mark.freeze_time("2026-11-20 12:00:00+10:00")
async def test_uses_saved_reading_within_the_month(
    hass: HomeAssistant, mock_api: AsyncMock, hass_storage: dict[str, Any]
) -> None:
    entry = _entry(hass)
    _save_reading(hass_storage, entry, "2026-11-01T18:05:00+00:00")
    await _setup(hass, entry)

    mock_api.get_collection.assert_not_awaited()
    assert hass.states.get(f"sensor.{PREFIX}_next_collection").state == "2026-11-24"
    assert hass.states.get(f"sensor.{PREFIX}_bins_to_put_out").state == "General waste & Recycling"


@pytest.mark.freeze_time("2026-11-20 12:00:00+10:00")
async def test_checks_on_the_first_of_the_month(
    hass: HomeAssistant,
    mock_api: AsyncMock,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    entry = _entry(hass)
    _save_reading(hass_storage, entry, "2026-11-01T18:05:00+00:00")
    await _setup(hass, entry)
    minute = zlib.crc32(entry.entry_id.encode()) % 60

    # The daily check time on an ordinary day doesn't contact the council.
    freezer.move_to(f"2026-11-21 {CHECK_HOUR:02d}:{minute:02d}:00+10:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    mock_api.get_collection.assert_not_awaited()

    # On the 1st it does.
    freezer.move_to(f"2026-12-01 {CHECK_HOUR:02d}:{minute:02d}:00+10:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert mock_api.get_collection.await_count == 1
    assert hass.states.get(f"sensor.{PREFIX}_last_checked").state.startswith("2026-11-30T")


@pytest.mark.freeze_time("2026-12-02 12:00:00+10:00")
async def test_failed_check_keeps_saved_reading(
    hass: HomeAssistant, mock_api: AsyncMock, hass_storage: dict[str, Any]
) -> None:
    entry = _entry(hass)
    _save_reading(hass_storage, entry, "2026-11-01T18:05:00+00:00")
    mock_api.get_collection.side_effect = CannotConnect
    await _setup(hass, entry)

    # The check was due (none yet in December) and failed, but the saved
    # reading keeps the sensors working.
    assert entry.state is ConfigEntryState.LOADED
    assert mock_api.get_collection.await_count == 1
    assert hass.states.get(f"sensor.{PREFIX}_next_collection").state == "2026-12-08"
    assert entry.runtime_data.check_due()


@pytest.mark.freeze_time("2026-11-16 12:00:00+10:00")
async def test_button_notifies_when_the_council_changes(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    entry = _entry(hass)
    await _setup(hass, entry)
    assert (
        hass.states.get(f"sensor.{PREFIX}_bins_to_put_out").state == "General waste & Green waste"
    )

    mock_api.get_collection.return_value = RECYCLE_WEEK
    with patch(f"{NOTIFY}.async_create") as create:
        await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
        await hass.async_block_till_done()

    create.assert_called_once()
    message = create.call_args.args[1]
    assert ADDRESS in message
    assert "Expected: Tuesday 17 November: General waste & Green waste" in message
    assert "Council now says: Tuesday 17 November: General waste & Recycling" in message
    assert hass.states.get(f"sensor.{PREFIX}_bins_to_put_out").state == "General waste & Recycling"


@pytest.mark.freeze_time("2026-11-16 12:00:00+10:00")
async def test_button_is_quiet_when_nothing_changed(
    hass: HomeAssistant, mock_api: AsyncMock
) -> None:
    entry = _entry(hass)
    await _setup(hass, entry)
    last_changed = hass.states.get(f"sensor.{PREFIX}_last_changed").state

    with patch(f"{NOTIFY}.async_create") as create:
        await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
        await hass.async_block_till_done()

    create.assert_not_called()
    assert mock_api.get_collection.await_count == 2
    assert hass.states.get(f"sensor.{PREFIX}_last_changed").state == last_changed


@pytest.mark.freeze_time("2026-11-16 12:00:00+10:00")
async def test_button_reports_errors(hass: HomeAssistant, mock_api: AsyncMock) -> None:
    entry = _entry(hass)
    await _setup(hass, entry)

    mock_api.get_collection.side_effect = CannotConnect("council down")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("button", "press", {"entity_id": BUTTON}, blocking=True)
    assert hass.states.get(f"sensor.{PREFIX}_next_collection").state == "2026-11-17"


async def test_removing_property_deletes_saved_reading(
    hass: HomeAssistant, mock_api: AsyncMock, hass_storage: dict[str, Any]
) -> None:
    entry = _entry(hass)
    await _setup(hass, entry)
    assert f"{DOMAIN}.{entry.entry_id}" in hass_storage

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert f"{DOMAIN}.{entry.entry_id}" not in hass_storage
