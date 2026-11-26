"""Data coordinator for Bin Collection Toowoomba QLD."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import AddressNotFound, BinCollection, ToowoombaBinApi, ToowoombaBinError
from .const import CONF_ADDRESS, CONF_GREEN_SERVICE, DOMAIN, STORAGE_VERSION

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
    last_checked: datetime | None = None
    last_changed: datetime | None = None

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


def _outcome(schedule: BinSchedule) -> tuple[date, bool, bool, bool]:
    """The parts of a schedule people act on: the day and which bins go out."""
    return (
        schedule.collection_date,
        schedule.general_waste,
        schedule.recycling,
        schedule.green_waste,
    )


def _describe(schedule: BinSchedule) -> str:
    day = schedule.collection_date
    return f"{day:%A} {day.day} {day:%B}: {' & '.join(schedule.bins)}"


class ToowoombaBinCoordinator(DataUpdateCoordinator[BinSchedule]):
    """Keeps the council's last reading for one address and projects it forward.

    The council's site is checked on the 1st of each month (a missed or failed
    check is retried daily until one succeeds that month) or when the user
    presses the check button. In between, the saved reading is rolled forward
    each day without contacting the council.
    """

    config_entry: ToowoombaBinConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ToowoombaBinConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=None,
        )
        self.api = ToowoombaBinApi(async_get_clientsession(hass))
        self.address: str = entry.data[CONF_ADDRESS]
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._loaded = False
        self._collection: BinCollection | None = None
        self._last_checked: datetime | None = None
        self._last_changed: datetime | None = None

    def check_due(self) -> bool:
        """True when this month's check of the council's site hasn't succeeded yet."""
        if self._collection is None or self._last_checked is None:
            return True
        today = dt_util.now().date()
        return dt_util.as_local(self._last_checked).date() < today.replace(day=1)

    def build(self) -> BinSchedule:
        """The schedule from the saved reading, as of today."""
        assert self._collection is not None
        schedule = build_schedule(
            self._collection,
            dt_util.now().date(),
            self.config_entry.data.get(CONF_GREEN_SERVICE, False),
        )
        return replace(schedule, last_checked=self._last_checked, last_changed=self._last_changed)

    async def _async_update_data(self) -> BinSchedule:
        if not self._loaded:
            await self._async_load()
        if self.check_due():
            try:
                await self._async_check()
            except UpdateFailed:
                if self._collection is None:
                    raise
                # Keep showing the saved reading; the daily check retries.
                _LOGGER.warning(
                    "Could not check the council's site for %s; using the saved reading",
                    self.address,
                    exc_info=True,
                )
        return self.build()

    async def async_check_now(self) -> None:
        """Check the council's site now and notify if the next collection changed."""
        before = self.data
        try:
            changed = await self._async_check()
        except UpdateFailed as err:
            raise HomeAssistantError(str(err)) from err
        after = self.build()
        self.async_set_updated_data(after)
        if changed and before is not None:
            persistent_notification.async_create(
                self.hass,
                f"The council's bin collection for **{self.address}** has changed.\n\n"
                f"- Expected: {_describe(before)}\n"
                f"- Council now says: {_describe(after)}",
                title="Bin collection changed",
                notification_id=f"{DOMAIN}_{self.config_entry.entry_id}_changed",
            )

    async def _async_check(self) -> bool:
        """Fetch the council's reading and save it. True if the next collection changed."""
        before = self.build() if self._collection is not None else None
        try:
            collection = await self.api.get_collection(self.address)
        except AddressNotFound as err:
            raise UpdateFailed(f"No collection found for {self.address}: {err}") from err
        except ToowoombaBinError as err:
            raise UpdateFailed(f"Error talking to the council service: {err}") from err
        if collection.collection_date is None:
            raise UpdateFailed("Council did not return a collection date")

        # Green waste is an optional service; remember it once we have seen it
        # so off-weeks can be predicted correctly.
        entry = self.config_entry
        if collection.green_waste and not entry.data.get(CONF_GREEN_SERVICE):
            self.hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_GREEN_SERVICE: True}
            )

        now = dt_util.utcnow()
        self._collection = collection
        self._last_checked = now
        changed = before is None or _outcome(before) != _outcome(self.build())
        if changed:
            self._last_changed = now
        await self._store.async_save(self._serialize())
        return changed and before is not None

    async def _async_load(self) -> None:
        self._loaded = True
        stored = await self._store.async_load()
        if not stored:
            return
        try:
            raw = stored["collection"]
            self._collection = BinCollection(
                address=raw["address"],
                description=raw["description"],
                collection_date=date.fromisoformat(raw["collection_date"]),
                image_url=raw.get("image_url"),
            )
            self._last_checked = dt_util.parse_datetime(stored["last_checked"])
            if last_changed := stored.get("last_changed"):
                self._last_changed = dt_util.parse_datetime(last_changed)
        except (KeyError, TypeError, ValueError):
            _LOGGER.warning("Ignoring unreadable saved reading for %s", self.address)
            self._collection = None
            self._last_checked = None

    def _serialize(self) -> dict[str, Any]:
        assert self._collection is not None and self._last_checked is not None
        c = self._collection
        return {
            "collection": {
                "address": c.address,
                "description": c.description,
                "collection_date": c.collection_date.isoformat() if c.collection_date else None,
                "image_url": c.image_url,
            },
            "last_checked": self._last_checked.isoformat(),
            "last_changed": self._last_changed.isoformat() if self._last_changed else None,
        }


async def async_remove_saved_reading(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete a property's saved reading when it is removed."""
    await Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}").async_remove()
