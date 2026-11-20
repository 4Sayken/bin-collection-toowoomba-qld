"""Client for the Toowoomba Regional Council waste collection lookup.

The council website embeds a Boomi Flow form. Address suggestions come from a
plain REST endpoint, while the weekly collection is produced by running the
flow: start a state, submit the chosen address with the "Search" outcome, then
read the "Bin information" HTML block from the response.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import html
import re
from typing import Any

import aiohttp

ADDRESS_URL = "https://apigateway.tr.qld.gov.au/ws/rest/v1/Property"
FLOW_BASE_URL = "https://au.flow-prod.boomi.com/api/run/2"
TENANT_ID = "8c3baeb7-fb90-479f-83c8-ce79bb5efa56"
FLOW_ID = "6f11c501-9c9c-49cf-b35c-3aff7fe7f08e"
PLAYER_URL = f"https://au.flow-prod.boomi.com/{TENANT_ID}/play/TRC-Forms-Prod/?flow-id={FLOW_ID}"

MIN_QUERY_LENGTH = 4
TIMEOUT = aiohttp.ClientTimeout(total=30)

_FIELD_RE = r"<strong>\s*{label}\s*:?\s*</strong>\s*(?:<br\s*/?>)?\s*(.*?)\s*</p>"


class ToowoombaBinError(Exception):
    """Base error for the bin lookup."""


class CannotConnect(ToowoombaBinError):
    """The council service could not be reached or answered unexpectedly."""


class AddressNotFound(ToowoombaBinError):
    """The council service returned no collection for the address."""


@dataclass(frozen=True, slots=True)
class BinCollection:
    """This week's collection for one property."""

    address: str
    description: str
    collection_date: date | None
    image_url: str | None

    @property
    def general_waste(self) -> bool:
        """General waste (red lid) goes out every week the service runs."""
        return "general" in self.description.lower()

    @property
    def recycling(self) -> bool:
        """Recycling (yellow lid) is collected this week."""
        return "recycl" in self.description.lower()

    @property
    def green_waste(self) -> bool:
        """Green waste (green lid) is collected this week."""
        return "green" in self.description.lower()

    @property
    def bins(self) -> list[str]:
        """Names of the bins going out this week."""
        names = []
        if self.general_waste:
            names.append("General waste")
        if self.recycling:
            names.append("Recycling")
        if self.green_waste:
            names.append("Green waste")
        return names


class ToowoombaBinApi:
    """Talks to the council address search and the Boomi Flow form."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def search_addresses(self, query: str) -> list[str]:
        """Return council-formatted addresses matching a partial address."""
        query = query.strip()
        if len(query) < MIN_QUERY_LENGTH:
            return []
        data = await self._request("GET", ADDRESS_URL, params={"address": query})
        if not isinstance(data, list):
            return []
        return [
            item["Formatted_Address"]
            for item in data
            if isinstance(item, dict) and item.get("Formatted_Address")
        ]

    async def get_collection(self, address: str) -> BinCollection:
        """Run the flow for an address and return this week's collection."""
        state = await self._request(
            "POST",
            FLOW_BASE_URL,
            json={
                "flowId": {"id": FLOW_ID, "versionId": None},
                "inputs": None,
                "playerUrl": PLAYER_URL,
                "joinPlayerUrl": PLAYER_URL,
                "mode": None,
                "reportingMode": None,
            },
        )
        state_id = state.get("stateId") if isinstance(state, dict) else None
        if not state_id:
            raise CannotConnect("Flow did not return a state")

        state_url = f"{FLOW_BASE_URL}/state/{state_id}"
        page = await self._request(
            "POST",
            state_url,
            json={
                "invokeType": "FORWARD",
                "stateId": state_id,
                "stateToken": state.get("stateToken"),
                "currentMapElementId": state.get("currentMapElementId"),
                "mapElementInvokeRequest": {},
                "mode": None,
            },
        )

        components = _components(page.get("rootElement"))
        address_component = next((c for c in components if c.get("type") == "addresssearch"), None)
        outcome = next(
            (
                o
                for o in page.get("outcomes") or []
                if (o.get("label") or o.get("developerName")) == "Search"
            ),
            None,
        )
        if address_component is None or outcome is None:
            raise CannotConnect("Council form layout has changed")

        result = await self._request(
            "POST",
            state_url,
            json={
                "invokeType": "FORWARD",
                "stateId": state_id,
                "stateToken": page.get("stateToken"),
                "currentMapElementId": page.get("currentMapElementId"),
                "mapElementInvokeRequest": {
                    "pageRequest": {
                        "pageComponentInputResponses": [
                            {
                                "pageComponentId": c["id"],
                                "contentValue": address if c is address_component else None,
                                "objectData": [],
                                "attributes": None,
                            }
                            for c in components
                        ]
                    },
                    "selectedOutcomeId": outcome["id"],
                },
                "mode": None,
            },
        )

        info = next(
            (
                c
                for c in _components(result.get("rootElement"))
                if c.get("developerName") == "Bin information"
            ),
            None,
        )
        if info is None or not info.get("isVisible"):
            raise AddressNotFound(_error_text(result) or address)
        return _parse_collection(info.get("content") or "", address)

    async def _request(self, method: str, url: str, **kwargs: Any) -> Any:
        headers = {"ManyWhoTenant": TENANT_ID} if url.startswith(FLOW_BASE_URL) else {}
        try:
            async with self._session.request(
                method, url, headers=headers, timeout=TIMEOUT, **kwargs
            ) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CannotConnect(str(err)) from err


def _components(element: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Flatten the page tree into its leaf components, in page order."""
    if not element:
        return []
    found: list[dict[str, Any]] = []
    for child in element.get("children") or []:
        if child.get("$type") == "container":
            found.extend(_components(child))
        else:
            found.append(child)
    return found


def _error_text(page: dict[str, Any]) -> str | None:
    for c in _components(page.get("rootElement")):
        if c.get("developerName") == "Error container" and c.get("isVisible"):
            return _strip_tags(c.get("content") or "") or None
    return None


def _strip_tags(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", text)).split())


def _field(content: str, label: str) -> str | None:
    match = re.search(_FIELD_RE.format(label=re.escape(label)), content, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _strip_tags(match.group(1)) or None


def _parse_collection(content: str, fallback_address: str) -> BinCollection:
    description = _field(content, "This weeks collection")
    if not description:
        raise AddressNotFound(fallback_address)

    collection_date = None
    raw_date = _field(content, "This weeks collection date") or ""
    if match := re.search(r"\d{1,2}/\d{1,2}/\d{4}", raw_date):
        collection_date = datetime.strptime(match.group(0), "%d/%m/%Y").date()

    image = re.search(r'<img[^>]*\bsrc="([^"]+)"', content)
    return BinCollection(
        address=_field(content, "Address") or fallback_address,
        description=description,
        collection_date=collection_date,
        image_url=image.group(1) if image and image.group(1) else None,
    )
