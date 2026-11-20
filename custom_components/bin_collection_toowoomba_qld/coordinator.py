"""Data coordinator for Bin Collection Toowoomba QLD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AddressNotFound, BinCollection, ToowoombaBinApi, ToowoombaBinError
from .const import CONF_ADDRESS, CONF_GREEN_SERVICE, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type ToowoombaBinConfigEntry = ConfigEntry[ToowoombaBinCoordinator]


@dataclass(frozen=True, slots=True)
class BinSchedule:
    """The next collection for a property."""

    address: str
    collection_date: date
    general_waste: bool
    recycling: bool
    green_waste: bool
    estimated: bool
    council_description: str
    council_date: date
    image_url: str | None
    green_service: bool

    @property
    def next_recycling(self) -> date:
        """Recycling alternates fortnightly, so it is this collection or the next."""
        if self.recycling:
            return self.collection_date
        return self.collection_date + timedelta(weeks=1)

    @property
    def next_green_waste(self) -> date | None:
        """Green waste runs on the weeks recycling doesn't, for properties with the service."""
        if self.green_waste:
            return self.collection_date
        if self.green_service:
            return self.collection_date + timedelta(weeks=1)
        return None

    @property
    def bins(self) -> list[str]:
        """Names of the bins going out at the next collection."""
        names = []
        if self.general_waste:
            names.append("General waste")
        if self.recycling:
            names.append("Recycling")
        if self.green_waste:
            names.append("Green waste")
        return names


def build_schedule(collection: BinCollection, today: date, green_service: bool) -> BinSchedule:
    """Project the council's "this week" answer onto the next collection day.

    The council keeps showing this week's collection after it has happened, so
    once that date has passed the next collection is rolled forward a week at a
    time. Recycling and green waste alternate fortnightly, so they swap on
    every odd week rolled.
    """
    council_date = collection.collection_date
    if council_date is None:
        raise UpdateFailed("Council did not return a collection date")

    if council_date >= today:
        return BinSchedule(
            address=collection.address,
            collection_date=council_date,
            general_waste=collection.general_waste,
            recycling=collection.recycling,
            green_waste=collection.green_waste,
            estimated=False,
            council_description=collection.description,
            council_date=council_date,
            image_url=collection.image_url,
            green_service=green_service or collection.green_waste,
        )

    weeks = -(-(today - council_date).days // 7)
    recycling = collection.recycling
    if weeks % 2:
        recycling = not recycling
    return BinSchedule(
        address=collection.address,
        collection_date=council_date + timedelta(weeks=weeks),
        general_waste=collection.general_waste,
        recycling=recycling,
        green_waste=green_service and not recycling,
        estimated=True,
        council_description=collection.description,
        council_date=council_date,
        image_url=collection.image_url,
        green_service=green_service,
    )


class ToowoombaBinCoordinator(DataUpdateCoordinator[BinSchedule]):
    """Fetches the collection for one address."""

    config_entry: ToowoombaBinConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ToowoombaBinConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.api = ToowoombaBinApi(async_get_clientsession(hass))
        self.address: str = entry.data[CONF_ADDRESS]

    async def _async_update_data(self) -> BinSchedule:
        try:
            collection = await self.api.get_collection(self.address)
        except AddressNotFound as err:
            raise UpdateFailed(f"No collection found for {self.address}: {err}") from err
        except ToowoombaBinError as err:
            raise UpdateFailed(f"Error talking to the council service: {err}") from err

        # Green waste is an optional service; remember it once we have seen it
        # so off-weeks can be predicted correctly.
        entry = self.config_entry
        if collection.green_waste and not entry.data.get(CONF_GREEN_SERVICE):
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_GREEN_SERVICE: True}
            )

        return build_schedule(
            collection,
            dt_util.now().date(),
            entry.data.get(CONF_GREEN_SERVICE, False),
        )
