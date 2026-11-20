"""Binary sensors for Toowoomba Bin Schedule."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import BinSchedule, ToowoombaBinConfigEntry, ToowoombaBinCoordinator
from .entity import ToowoombaBinEntity

PARALLEL_UPDATES = 0


def _bins_out(schedule: BinSchedule) -> bool:
    """Bins belong on the kerb from the day before until collection day ends."""
    today = dt_util.now().date()
    return schedule.collection_date - timedelta(days=1) <= today <= schedule.collection_date


@dataclass(frozen=True, kw_only=True)
class ToowoombaBinBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a bin schedule binary sensor."""

    is_on_fn: Callable[[BinSchedule], bool]


BINARY_SENSORS: tuple[ToowoombaBinBinarySensorDescription, ...] = (
    ToowoombaBinBinarySensorDescription(
        key="recycling_week",
        is_on_fn=lambda s: s.recycling,
    ),
    ToowoombaBinBinarySensorDescription(
        key="green_waste_week",
        is_on_fn=lambda s: s.green_waste,
    ),
    ToowoombaBinBinarySensorDescription(
        key="bins_out",
        is_on_fn=_bins_out,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ToowoombaBinConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up bin schedule binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(ToowoombaBinBinarySensor(coordinator, d) for d in BINARY_SENSORS)


class ToowoombaBinBinarySensor(ToowoombaBinEntity, BinarySensorEntity):
    """A bin schedule binary sensor."""

    entity_description: ToowoombaBinBinarySensorDescription

    def __init__(
        self,
        coordinator: ToowoombaBinCoordinator,
        description: ToowoombaBinBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.is_on_fn(self.coordinator.data)
