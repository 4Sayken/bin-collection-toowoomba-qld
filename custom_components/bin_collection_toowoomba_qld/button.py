"""Button for Bin Collection Toowoomba QLD."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ToowoombaBinConfigEntry, ToowoombaBinCoordinator
from .entity import ToowoombaBinEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ToowoombaBinConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the check-for-changes button."""
    async_add_entities([ToowoombaBinCheckButton(entry.runtime_data)])


class ToowoombaBinCheckButton(ToowoombaBinEntity, ButtonEntity):
    """Checks the council's site now instead of waiting for the monthly check."""

    def __init__(self, coordinator: ToowoombaBinCoordinator) -> None:
        super().__init__(coordinator, "check_now")

    async def async_press(self) -> None:
        await self.coordinator.async_check_now()
