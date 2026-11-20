"""Config flow for Bin Collection Toowoomba QLD."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .api import MIN_QUERY_LENGTH, AddressNotFound, CannotConnect, ToowoombaBinApi
from .const import CONF_ADDRESS, CONF_GREEN_SERVICE, DOMAIN

_LOGGER = logging.getLogger(__name__)

CONF_SEARCH = "search"


class ToowoombaBinConfigFlow(ConfigFlow, domain=DOMAIN):
    """Search for an address, then pick the council's match."""

    VERSION = 1

    def __init__(self) -> None:
        self._matches: list[str] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for part of the street address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            query = user_input[CONF_SEARCH].strip()
            if len(query) < MIN_QUERY_LENGTH:
                errors[CONF_SEARCH] = "too_short"
            else:
                api = ToowoombaBinApi(async_get_clientsession(self.hass))
                try:
                    self._matches = await api.search_addresses(query)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                else:
                    if self._matches:
                        return await self.async_step_select()
                    errors[CONF_SEARCH] = "no_results"

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_SEARCH): TextSelector()}), user_input
            ),
            errors=errors,
        )

    async def async_step_select(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Pick the matching property and check it has a collection."""
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(address.lower())
            self._abort_if_unique_id_configured()

            api = ToowoombaBinApi(async_get_clientsession(self.hass))
            try:
                collection = await api.get_collection(address)
            except AddressNotFound:
                errors["base"] = "no_collection"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error looking up %s", address)
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=collection.address,
                    data={
                        CONF_ADDRESS: address,
                        CONF_GREEN_SERVICE: collection.green_waste,
                    },
                )

        return self.async_show_form(
            step_id="select",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(options=self._matches, mode=SelectSelectorMode.LIST)
                    )
                }
            ),
            errors=errors,
        )
