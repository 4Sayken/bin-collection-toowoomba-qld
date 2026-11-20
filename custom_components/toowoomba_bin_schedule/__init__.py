"""The Toowoomba Bin Schedule integration."""

from __future__ import annotations

from datetime import datetime

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .coordinator import ToowoombaBinConfigEntry, ToowoombaBinCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ToowoombaBinConfigEntry) -> bool:
    """Set up Toowoomba Bin Schedule from a config entry."""
    coordinator = ToowoombaBinCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async def _refresh_after_midnight(_now: datetime) -> None:
        # Date-based states ("bins out tonight") must roll over with the day.
        await coordinator.async_request_refresh()

    entry.async_on_unload(
        async_track_time_change(hass, _refresh_after_midnight, hour=0, minute=1, second=0)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ToowoombaBinConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
