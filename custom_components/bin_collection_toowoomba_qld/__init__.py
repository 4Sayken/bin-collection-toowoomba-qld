"""The Bin Collection Toowoomba QLD integration."""

from __future__ import annotations

from datetime import datetime
import zlib

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .const import CHECK_HOUR
from .coordinator import (
    ToowoombaBinConfigEntry,
    ToowoombaBinCoordinator,
    async_remove_saved_reading,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ToowoombaBinConfigEntry) -> bool:
    """Set up Bin Collection Toowoomba QLD from a config entry."""
    coordinator = ToowoombaBinCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async def _roll_over_day(_now: datetime) -> None:
        # Date-based states ("bin night") must change with the day; this uses
        # the saved reading and doesn't contact the council.
        coordinator.async_set_updated_data(coordinator.build())

    async def _monthly_check(_now: datetime) -> None:
        # Runs daily but only contacts the council when this month's check is
        # still due, which is the 1st unless a check failed or was missed.
        if coordinator.check_due():
            await coordinator.async_refresh()

    entry.async_on_unload(async_track_time_change(hass, _roll_over_day, hour=0, minute=1, second=0))
    entry.async_on_unload(
        async_track_time_change(
            hass,
            _monthly_check,
            hour=CHECK_HOUR,
            minute=zlib.crc32(entry.entry_id.encode()) % 60,
            second=0,
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ToowoombaBinConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the property's saved reading."""
    await async_remove_saved_reading(hass, entry)
