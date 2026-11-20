"""Fixtures for Bin Collection Toowoomba QLD tests."""

from collections.abc import Generator
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.bin_collection_toowoomba_qld.api import BinCollection

ADDRESS = "3 Parsons Street RANGEVILLE QLD 4350"

GREEN_WEEK = BinCollection(
    address=ADDRESS,
    description="General & Greenwaste",
    collection_date=date(2026, 11, 17),
    image_url="https://example.com/Greenwaste.jpg",
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load integrations from custom_components."""


@pytest.fixture
def mock_api() -> Generator[AsyncMock]:
    """Patch the council API wherever it is constructed."""
    api = AsyncMock()
    api.search_addresses.return_value = [ADDRESS]
    api.get_collection.return_value = GREEN_WEEK
    with (
        patch(
            "custom_components.bin_collection_toowoomba_qld.config_flow.ToowoombaBinApi",
            return_value=api,
        ),
        patch(
            "custom_components.bin_collection_toowoomba_qld.coordinator.ToowoombaBinApi",
            return_value=api,
        ),
    ):
        yield api
