"""Tests for HTML parsing and next-collection projection."""

from datetime import date

import pytest

from custom_components.toowoomba_bin_schedule.api import (
    AddressNotFound,
    BinCollection,
    _parse_collection,
)
from custom_components.toowoomba_bin_schedule.coordinator import build_schedule

# Copied from a live council response on 2026-11-20.
COUNCIL_HTML = (
    "<p>Please place your bins out on the kerb the night before collection day.</p>\n"
    '<p>&nbsp;</p>\n<div class="properties-bin"><img id="binImage" style="width: 100%;" '
    'src="https://master-boomi-flow-assets-prod-ap-southeast-2.s3.amazonaws.com/x/Greenwaste.jpg" alt="Bin Image">\n'  # noqa: E501
    '<div class="bin-info">\n'
    "<p><strong>Address:</strong><br>3 Parsons Street RANGEVILLE QLD 4350</p>\n"
    "<p><strong>This weeks collection:</strong><br>General & Greenwaste</p>\n"
    "<p><strong>This weeks collection date:</strong><br>Tuesday 17/11/2026</p>\n"
    "</div>\n</div>"
)

EMPTY_HTML = (
    '<div class="bin-info">\n<p><strong>Address:</strong><br></p>\n'
    "<p><strong>This weeks collection:</strong><br></p>\n"
    "<p><strong>This weeks collection date:</strong><br> </p>\n</div>"
)


def test_parse_council_html() -> None:
    c = _parse_collection(COUNCIL_HTML, "fallback")
    assert c.address == "3 Parsons Street RANGEVILLE QLD 4350"
    assert c.description == "General & Greenwaste"
    assert c.collection_date == date(2026, 11, 17)
    assert c.image_url.endswith("Greenwaste.jpg")
    assert c.bins == ["General waste", "Green waste"]


def test_parse_empty_raises() -> None:
    with pytest.raises(AddressNotFound):
        _parse_collection(EMPTY_HTML, "fallback")


def test_recycle_wording() -> None:
    c = BinCollection("a", "General & Recycle", date(2026, 11, 18), None)
    assert (c.general_waste, c.recycling, c.green_waste) == (True, True, False)


GREEN = BinCollection("a", "General & Greenwaste", date(2026, 11, 17), None)
RECYCLE = BinCollection("a", "General & Recycle", date(2026, 11, 17), None)


@pytest.mark.parametrize(
    ("collection", "today", "green_service", "expected"),
    [
        # Before or on collection day: council answer as-is.
        (GREEN, date(2026, 11, 16), True, (date(2026, 11, 17), False, True, False)),
        (GREEN, date(2026, 11, 17), True, (date(2026, 11, 17), False, True, False)),
        # One week rolled: swap to recycling.
        (GREEN, date(2026, 11, 18), True, (date(2026, 11, 24), True, False, True)),
        (RECYCLE, date(2026, 11, 20), True, (date(2026, 11, 24), False, True, True)),
        # No green service: off-week is general waste only.
        (RECYCLE, date(2026, 11, 20), False, (date(2026, 11, 24), False, False, True)),
        # Two weeks rolled (council stale): same as the council week.
        (RECYCLE, date(2026, 11, 25), True, (date(2026, 12, 1), True, False, True)),
    ],
)
def test_build_schedule(collection, today, green_service, expected) -> None:
    s = build_schedule(collection, today, green_service)
    assert (s.collection_date, s.recycling, s.green_waste, s.estimated) == expected
    assert s.general_waste
