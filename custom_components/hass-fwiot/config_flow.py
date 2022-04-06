"""Config flow for Hello World integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .fwiot import FWIOTSystem, FWIOTDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# This is the schema that used to display the UI to the user. This simple
# schema has a single required host field, but it could include a number of fields
# such as username, password etc. See other components in the HA core code for
# further examples.
# Note the input displayed to the user will be translated. See the
# translations/<lang>.json file and strings.json. See here for further information:
# https://developers.home-assistant.io/docs/config_entries_config_flow_handler/#translations
# At the time of writing I found the translations created by the scaffold didn't
# quite work as documented and always gave me the "Lokalise key references" string
# (in square brackets), rather than the actual translated value. I did not attempt to
# figure this out or look further into it.
DATA_SCHEMA = vol.Schema({("api_key"): str})

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.

    # This is a simple example to show an error in the UI for a short hostname
    # The exceptions are defined at the end of this file, and are used in the
    # `async_step_user` method below.
    _LOGGER.info(data)
    if len(data.get("api_key",'')) != 36:
        raise InvalidAPIKey
    
    if not DOMAIN in hass.data:
       hass.data[DOMAIN] = FWIOTSystem(hass)
    
    fwsys:FWIOTSystem = hass.data[DOMAIN]   
    # The dummy hub provides a `test_connection` method to ensure it's working
    # as expected
    # result = await fwiot.test_connection()
    # if not result:
    #     # If there is an error, raise an exception to notify HA that there was a
    #     # problem. The UI will also show there was a problem
    #     raise CannotConnect

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    try:
        ss = await hass.async_add_executor_job(
            fwsys.get_device, data["api_key"]
        )
        fwsys.devices[ss].coordinator = FWIOTDataUpdateCoordinator(hass, fwsys.devices[ss])
        await fwsys.devices[ss].coordinator.async_config_entry_first_refresh()

    except:
        raise CannotConnect

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    # "Title" is what is displayed to the user for this hub device
    # It is stored internally in HA as part of the device config.
    # See `async_step_user` below for how this is used
    return

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FWIOT."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
        errors = {}
        if user_input is not None:
            
            try:
                info = await validate_input(self.hass, user_input)

                ks = []
                ks.append(user_input.get('api_key'))

                return self.async_create_entry(title='Devices', data={"keys":ks})
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except DeviceAlreadyExist:
                errors["base"] = "device_exist"
            except InvalidAPIData:
                errors["base"] = "invalid_api_data"
            except InvalidAPIKey:
                # The error string is set here, and should be translated.
                # This example does not currently cover translations, see the
                # comments on `DATA_SCHEMA` for further details.
                # Set the error on the `host` field, not the entire form.
                errors["base"] = "invalid_api"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(entry)

class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAPIData(exceptions.HomeAssistantError):
    """Error to indicate get wrong api data (no serial)."""

class DeviceAlreadyExist(exceptions.HomeAssistantError):
    """Error to indicate device already added."""

class InvalidAPIKey(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid api key."""

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        # This goes through the steps to take the user through the setup process.
        # Using this it is possible to update the UI and prompt for additional
        # information. This example provides a single form (built from `DATA_SCHEMA`),
        # and when that has some validated input, it calls `async_create_entry` to
        # actually create the HA config entry. Note the "title" value is returned by
        # `validate_input` above.
        errors = {}
        if user_input is not None:
            
            try:
                info = await validate_input(self.hass, user_input)

                ks = self.config_entry.data.get('keys', [])
                ks.append(user_input.get('api_key'))
                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self.config_entry.entry_id)
                )
                return self.async_create_entry(title='Devices', data={"keys":ks})
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except DeviceAlreadyExist:
                errors["base"] = "device_exist"
            except InvalidAPIData:
                errors["base"] = "invalid_api_data"
            except InvalidAPIKey:
                # The error string is set here, and should be translated.
                # This example does not currently cover translations, see the
                # comments on `DATA_SCHEMA` for further details.
                # Set the error on the `host` field, not the entire form.
                errors["base"] = "invalid_api"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )