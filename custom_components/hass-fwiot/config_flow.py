"""Config flow for the FWIOT component."""
from __future__ import annotations

import voluptuous as vol

from http import HTTPStatus
from typing import Any, cast

from requests.exceptions import ConnectTimeout, HTTPError

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_POLLING, DEFAULT_CACHEDB, DOMAIN, LOGGER

class FWIOTFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for FWIOT."""

    async def async_step_user(self, info):
        if info is not None:
            pass  # TODO: process info

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({vol.Required("password"): str})
        )