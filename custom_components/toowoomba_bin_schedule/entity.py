"""Base entity for Toowoomba Bin Schedule."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN
from .coordinator import ToowoombaBinCoordinator


class ToowoombaBinEntity(CoordinatorEntity[ToowoombaBinCoordinator]):
    """One entity per address, grouped under a service device."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: ToowoombaBinCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=coordinator.address,
            manufacturer="Toowoomba Regional Council",
            model="Waste collection",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=(
                "https://www.tr.qld.gov.au/Waste-and-water/Waste-and-recycling/"
                "Your-waste-bins-%e2%80%93-general-recycling-and-green-waste"
            ),
        )
