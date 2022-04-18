"""Config flow for Hello World integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import pytz

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN,\
                   FIELD_API, FIELD_TYPE, FIELD_IP, FIELD_PORT,\
                   FIELD_TZ, FIELD_UPDATE_EVERY,\
                   FLOWTYPE_FINGER, FLOWTYPE_IOT
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

async def validate_input(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    # Validate the data can be used to set up a connection.

    # This is a simple example to show an error in the UI for a short hostname
    # The exceptions are defined at the end of this file, and are used in the
    # `async_step_user` method below.
    if len(data.get(FIELD_API,'')) != 36:
        raise ErrorInvalidAPIKey
    
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
            fwsys.get_device, data[FIELD_API]
        )
        fwsys.devices[ss].coordinator = FWIOTDataUpdateCoordinator(hass, fwsys.devices[ss])
        await fwsys.devices[ss].coordinator.async_config_entry_first_refresh()

    except Exception as e:
        if e.args[0] == 1:
           raise ErrorCannotConnect
        elif e.args[0] == 2:
           raise ErrorDeviceAlreadyExist
        elif e.args[0] == 3:
           raise ErrorDeviceNotImplement
        elif e.args[0] == 4:
           raise ErrorInvalidAPIData

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    # "Title" is what is displayed to the user for this hub device
    # It is stored internally in HA as part of the device config.
    # See `async_step_user` below for how this is used
    return

async def validate_finger_ip(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    import re
    
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$",data.get(FIELD_IP,'')):
       raise ErrorInvalidIP

    if not data.get(FIELD_PORT,0):
       raise ErrorInvalidPort 

    try:
       tt = pytz.timezone(data.get(FIELD_TZ)) 
    except:
       raise ErrorInvalidTZ 

    if not DOMAIN in hass.data:
       hass.data[DOMAIN] = FWIOTSystem(hass)
    
    fwsys:FWIOTSystem = hass.data[DOMAIN]   
    try:
        ss = await hass.async_add_executor_job(
            fwsys.check_finger, data[FIELD_IP], data[FIELD_PORT], data[FIELD_TZ]
        )
        fwsys.devices[ss].coordinator = FWIOTDataUpdateCoordinator(hass, fwsys.devices[ss])
        await fwsys.devices[ss].coordinator.async_config_entry_first_refresh()

    except Exception as e:
        print(e)
        if e.args[0] == 2:
           raise ErrorDeviceAlreadyExist
        else:
           raise ErrorCannotConnectFinger
    
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
        if user_input is None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required(FIELD_TYPE, default=FLOWTYPE_IOT): vol.In(
                            (
                                FLOWTYPE_IOT,
                                FLOWTYPE_FINGER,
                            )
                        )
                    })
                )

        if user_input[FIELD_TYPE] == FLOWTYPE_FINGER:
           return await self.async_step_finger()
        return await self.async_step_iot()

    async def async_step_iot(self, user_input=None):        
        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)

                ks = {user_input.get(FIELD_API):{
                    'type':'iot'
                }}

                return self.async_create_entry(title='Devices', data={"keys":ks})
            except ErrorCannotConnect:
                errors["base"] = "cannot_connect"
            except ErrorDeviceAlreadyExist:
                errors["base"] = "device_exist"
            except ErrorInvalidAPIData:
                errors["base"] = "invalid_api_data"
            except ErrorDeviceNotImplement:
                errors["base"] = "not_implement"
            except ErrorInvalidAPIKey:
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
            step_id="iot", data_schema=vol.Schema({(FIELD_API): str}), errors=errors
        )

    async def async_step_finger(self, user_input=None):        
        errors = {}
        if user_input is not None:
            
            try:
                await validate_finger_ip(self.hass, user_input)

                ks = {user_input.get(FIELD_IP):{
                    'type':'finger',
                    'port': user_input.get(FIELD_PORT),
                    'tz': user_input.get(FIELD_TZ),
                    'every': user_input.get(FIELD_UPDATE_EVERY)
                }}

                return self.async_create_entry(title='Devices', data={"keys":ks})
            except ErrorInvalidIP:
                errors["base"] = "invalid_ip"
            except ErrorInvalidPort:
                errors["base"] = "invalid_port"
            except ErrorInvalidTZ:
                errors["base"] = "invalid_tz"
            except ErrorCannotConnectFinger:
                errors["base"] = "cannot_connectf"
            except ErrorDeviceAlreadyExist:
                errors["base"] = "device_exist"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="finger", data_schema=vol.Schema({
                vol.Required(FIELD_IP): str, 
                vol.Required(FIELD_PORT): int, 
                vol.Required(FIELD_TZ,default='Asia/Bangkok'): str,
                vol.Required(FIELD_UPDATE_EVERY,default=5): int,
            }), errors=errors
        )
    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        return OptionsFlowHandler(entry)

class ErrorCannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""

class ErrorInvalidAPIData(exceptions.HomeAssistantError):
    """Error to indicate get wrong api data (no serial)."""

class ErrorDeviceAlreadyExist(exceptions.HomeAssistantError):
    """Error to indicate device already added."""

class ErrorInvalidAPIKey(exceptions.HomeAssistantError):
    """Error to indicate there is an invalid api key."""

class ErrorDeviceNotImplement(exceptions.HomeAssistantError):
    """Error to indicate there device has not implement."""

class ErrorInvalidIP(exceptions.HomeAssistantError):
    """Error to indicate invalid ip."""

class ErrorInvalidPort(exceptions.HomeAssistantError):
    """Error to indicate invalid port."""

class ErrorCannotConnectFinger(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect fingerprint."""

class ErrorInvalidTZ(exceptions.HomeAssistantError):
    """Error to indicate invalid timezone."""

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
        if user_input is None:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema({
                        vol.Required(FIELD_TYPE, default=FLOWTYPE_IOT): vol.In(
                            (
                                FLOWTYPE_IOT,
                                FLOWTYPE_FINGER,
                            )
                        )
                    })
                )

        if user_input[FIELD_TYPE] == FLOWTYPE_FINGER:
           return await self.async_step_finger()
        return await self.async_step_iot()

    async def async_step_iot(self, user_input=None):        
        errors = {}
        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)

                ks = self.config_entry.data.get('keys', {})
                ks[user_input.get(FIELD_API)]={'type':'iot'}

                self.hass.async_create_task(
                    self.hass.config_entries.async_reload(self.config_entry.entry_id)
                )

                return self.async_create_entry(title='Devices', data={"keys":ks})
            except ErrorCannotConnect:
                errors["base"] = "cannot_connect"
            except ErrorDeviceAlreadyExist:
                errors["base"] = "device_exist"
            except ErrorInvalidAPIData:
                errors["base"] = "invalid_api_data"
            except ErrorDeviceNotImplement:
                errors["base"] = "not_implement"
            except ErrorInvalidAPIKey:
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
            step_id="iot", data_schema=vol.Schema({(FIELD_API): str}), errors=errors
        )

    async def async_step_finger(self, user_input=None):        
        errors = {}
        if user_input is not None:
            
            try:
                await validate_finger_ip(self.hass, user_input)

                ks = self.config_entry.data.get('keys', {})
                ks[user_input.get(FIELD_IP)]={
                    'type':'finger',
                    'port': user_input.get(FIELD_PORT),
                    'tz': user_input.get(FIELD_TZ),
                    'every': user_input.get(FIELD_UPDATE_EVERY)
                }

                return self.async_create_entry(title='Devices', data={"keys":ks})
            except ErrorInvalidIP:
                errors["base"] = "invalid_ip"
            except ErrorInvalidPort:
                errors["base"] = "invalid_port"
            except ErrorInvalidTZ:
                errors["base"] = "invalid_tz"
            except ErrorCannotConnect:
                errors["base"] = "cannot_connect"
            except ErrorDeviceAlreadyExist:
                errors["base"] = "device_exist"
            except ErrorCannotConnectFinger:
                errors["base"] = "cannot_connectf"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return self.async_show_form(
            step_id="finger", data_schema=vol.Schema({
                vol.Required(FIELD_IP): str, 
                vol.Required(FIELD_PORT): int, 
                vol.Required(FIELD_TZ,default='Asia/Bangkok'): str,
                vol.Required(FIELD_UPDATE_EVERY,default=5): int,
            }), errors=errors
        )
