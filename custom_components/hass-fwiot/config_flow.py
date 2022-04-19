"""Config flow for Hello World integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
import pytz

from homeassistant import config_entries, exceptions
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN,\
                   FIELD_API, FIELD_MODE, FIELD_TYPE, FIELD_IP, FIELD_PORT,\
                   FIELD_TZ, FIELD_UPDATE_EVERY,\
                   FIELD_MODE, FIELD_QUERY,\
                   FLOWTYPE_FINGER, FLOWTYPE_IOT,\
                   MODETYPE_ADD, MODETYPE_CHANGE
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

async def validate_api(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    """validate api key

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

    # Return info that you want to store in the config entry.
    # "Title" is what is displayed to the user for this hub device
    # It is stored internally in HA as part of the device config.
    # See `async_step_user` below for how this is used
    return

async def validate_finger_ip(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    ''' validate ip address, port, timezone '''
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
            fwsys.check_finger, data[FIELD_IP], data[FIELD_PORT], data[FIELD_TZ], data[FIELD_UPDATE_EVERY]
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

async def validate_finger_update(hass: HomeAssistant, data: dict) -> dict[str, Any]:
    ''' validate time zone '''
    import re
    
    try:
       tt = pytz.timezone(data.get(FIELD_TZ)) 
    except:
       raise ErrorInvalidTZ 
    
    return

async def form_choose_device(cf, user_input):
    ''' [flow:user] choose iot/finger '''
    if user_input is None:
                return cf.async_show_form(
                    step_id="device",
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
       return await cf.async_step_finger()
    return await cf.async_step_iot()

async def form_device_add_iot(cf, user_input):
    ''' [flow:iot] add iot device '''      
    errors = {}
    if user_input is not None:
        try:
            await validate_api(cf.hass, user_input)

            ks = {user_input.get(FIELD_API):{
                'type':'iot'
            }}

            return cf.async_create_entry(title='Devices', data={"keys":ks})
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
    return cf.async_show_form(
        step_id="iot", data_schema=vol.Schema({(FIELD_API): str}), errors=errors
    )

async def form_device_add_finger(cf, user_input):
        ''' [flow:finger] add fingerprint '''
        errors = {}
        if user_input is not None:
            
            try:
                await validate_finger_ip(cf.hass, user_input)

                ks = {user_input.get(FIELD_IP):{
                    'type':'finger',
                    'port': user_input.get(FIELD_PORT),
                    'tz': user_input.get(FIELD_TZ),
                    'every': user_input.get(FIELD_UPDATE_EVERY)
                }}

                return cf.async_create_entry(title='Devices', data={"keys":ks})
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
        return cf.async_show_form(
            step_id="finger", data_schema=vol.Schema({
                vol.Required(FIELD_IP): str, 
                vol.Required(FIELD_PORT): int, 
                vol.Required(FIELD_TZ,default='Asia/Bangkok'): str,
                vol.Required(FIELD_UPDATE_EVERY,default=5): int,
            }), errors=errors
        )

async def form_mode(cf, user_input):
    ''' [flow:mode] mode add / change '''
    if user_input is None:
            return cf.async_show_form(
                step_id="mode",
                data_schema=vol.Schema({
                    vol.Required(FIELD_MODE, default=MODETYPE_ADD): vol.In(
                        (
                            MODETYPE_ADD,
                            MODETYPE_CHANGE,
                        )
                    )
                })
            )

    if user_input[FIELD_MODE] == MODETYPE_ADD:
        return await cf.async_step_add()
    return await cf.async_step_find()

async def form_find(cf, user_input):
    ''' [flow:find] search device '''
    errors = {}
    if user_input is not None:

        ks = cf.config_entry.data.get('keys', {})
        if not user_input[FIELD_QUERY] in ks:
            errors["base"] = "device_notfound"
        else:
            ks[user_input[FIELD_QUERY]]['ip'] = user_input[FIELD_QUERY]
            cf.context['u-'+cf.flow_id] = user_input[FIELD_QUERY]
            return await cf.async_step_finger_update()

    return cf.async_show_form(
        step_id="find",
        data_schema=vol.Schema({
            vol.Required(FIELD_QUERY): str
        }), errors=errors
    )

async def form_update_finger(cf, user_input=None):
        ''' [flow:finger_update] update finger print '''
        errors = {}
        dt = (user_input or {}).get('dt', {})
        print(cf.context)
        if user_input is not None:
           try: 
                validate_finger_update(cf, user_input)

                # ks = cf.config_entry.data.get('keys', {})
                # ks[dt.get('ip')]['tz'] = user_input[FIELD_TZ]
                # ks[dt.get('ip')]['every'] = user_input[FIELD_UPDATE_EVERY]

                # cf.hass.config_entries.async_update_entry(
                #     cf,data={"keys":ks},
                # )
                return cf.async_abort(reason="updated successful")

           except ErrorInvalidTZ:
                errors["base"] = "invalid_tz"
           except Exception:  # pylint: disable=broad-except
               _LOGGER.exception("Unexpected exception")
               errors["base"] = "unknown"

        # If there is no user input or there were errors, show the form again, including any errors that were found with the input.
        return cf.async_show_form(
            step_id="finger_update", 
            description_placeholders={'ip': dt.get('ip'),'port': dt.get('port')},
            data_schema=vol.Schema({
                vol.Required(FIELD_TZ,default=dt.get('tz')): str,
                vol.Required(FIELD_UPDATE_EVERY,default=dt.get('every', 5)): int,
            }), errors=errors
        )

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for FWIOT."""

    VERSION = 1
    # Pick one of the available connection classes in homeassistant/config_entries.py
    # This tells HA if it should be asking for updates, or it'll be notified of updates
    # automatically. This example uses PUSH, as the dummy hub will notify HA of
    # changes.
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_init(self, user_input=None):
        return await self.async_step_device(user_input)

    async def async_step_device(self, user_input=None):  
        return await form_choose_device(user_input)

    async def async_step_iot(self, user_input=None):  
        return await form_device_add_iot(self, user_input)

    async def async_step_finger(self, user_input=None):        
        return await form_device_add_finger(self, user_input)

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
        return await self.async_step_mode(user_input)

    async def async_step_mode(self, user_input=None):
        return await form_mode(self, user_input)

    async def async_step_find(self, user_input=None):
        return await form_find(self, user_input)

    async def async_step_add(self, user_input=None):
        return await form_choose_device(self, user_input)

    async def async_step_iot(self, user_input=None):     
        return await form_device_add_iot(self, user_input)

    async def async_step_finger(self, user_input=None):   
        return await form_device_add_finger(self, user_input)

    async def async_step_finger_update(self, user_input=None):
        return await form_update_finger(self, user_input)
