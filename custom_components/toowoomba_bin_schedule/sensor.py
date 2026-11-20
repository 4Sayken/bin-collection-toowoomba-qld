"""Sensors for Toowoomba Bin Schedule."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import BinSchedule, ToowoombaBinConfigEntry, ToowoombaBinCoordinator
from .entity import ToowoombaBinEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class ToowoombaBinSensorDescription(SensorEntityDescription):
    """Describes a bin schedule sensor."""

    value_fn: Callable[[BinSchedule], date | int | str | None]


SENSORS: tuple[ToowoombaBinSensorDescription, ...] = (
    ToowoombaBinSensorDescription(
        key="next_collection",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda s: s.collection_date,
    ),
    ToowoombaBinSensorDescription(
        key="bins",
        value_fn=lambda s: " & ".join(s.bins) or None,
    ),
    ToowoombaBinSensorDescription(
        key="days_until_collection",
        native_unit_of_measurement=UnitOfTime.DAYS,
        value_fn=lambda s: (s.collection_date - dt_util.now().date()).days,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ToowoombaBinConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up bin schedule sensors."""
    coordinator = entry.runtime_data
    async_add_entities(ToowoombaBinSensor(coordinator, d) for d in SENSORS)


class ToowoombaBinSensor(ToowoombaBinEntity, SensorEntity):
    """A bin schedule sensor."""

    entity_description: ToowoombaBinSensorDescription

    def __init__(
        self,
        coordinator: ToowoombaBinCoordinator,
        description: ToowoombaBinSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> date | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.key != "next_collection":
            return None
        data = self.coordinator.data
        return {
            "address": data.address,
            "bins": data.bins,
            "general_waste": data.general_waste,
            "recycling": data.recycling,
            "green_waste": data.green_waste,
            "estimated": data.estimated,
            "council_collection": data.council_description,
            "council_collection_date": data.council_date.isoformat(),
            "bin_image": data.image_url,
        }
