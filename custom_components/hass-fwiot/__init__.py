"""The Detailed Hello World Push integration."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback, ServiceCall, Event
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_TOKEN, Platform, EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.dispatcher import dispatcher_send
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import fwiot
from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE,\
                   LOGGER, POLLING_TIMEOUT_SEC, UPDATE_INTERVAL,\
                   ATTR_SETTING, ATTR_VALUE, ATTR_ENTITY_ID,\
                   SERVICE_SETTINGS, CHANGE_SETTING_SCHEMA,\
                   SERVICE_CAPTURE_IMAGE, CAPTURE_IMAGE_SCHEMA,\
                   SERVICE_TRIGGER_AUTOMATION, AUTOMATION_SCHEMA 

# List of platforms to support. There should be a matching .py file for each,
# eg <cover.py> and <sensor.py>
# PLATFORMS: list[str] = ["cover"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up FWIOT from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    print('xxxxxxxxxxxxxxxxxxxxx')
    print(entry.data.get('keys'))
    print('xxxxxxxxxxxxxxxxxxxxx')
    fwsys = fwiot.FWIOTSystem(hass)
    fwsys.async_add_sensors = async_add_sensors

    if not DOMAIN in hass.data:
       hass.data[DOMAIN] = fwsys

    for each in entry.data.get('keys'):
        if not each in fwsys.devices:
           await hass.async_add_executor_job(fwsys.get_device, each)

    for each in fwsys.devices:
        fwsys.devices[each].coordinator = fwiot.FWIOTDataUpdateCoordinator(hass, fwsys.devices[each])
        await fwsys.devices[each].coordinator.async_config_entry_first_refresh()

    platforms = get_platforms(entry)

    #await async_create_device_and_coordinator(hass, entry)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    hass.config_entries.async_setup_platforms(entry, platforms)

    await setup_hass_events(hass)
    await hass.async_add_executor_job(setup_hass_services, hass)

    return True

async def setup_hass_events(hass: HomeAssistant) -> None:
    """Home Assistant start and stop callbacks."""

    def logout(event: Event) -> None:
         print('hass logout')

    hass.data[DOMAIN].logout_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, logout
    )

def setup_hass_services(hass: HomeAssistant) -> None:
    """Home Assistant services."""

    def change_setting(call: ServiceCall) -> None:
        """Change an system setting."""
        print('change_setting')
        pass

    def capture_image(call: ServiceCall) -> None:
        """Capture a new image."""
        print('capture_image')
        pass

    def trigger_automation(call: ServiceCall) -> None:
        """Trigger an automation."""
        print('trigger_automation')
        pass

    hass.services.register(
        DOMAIN, SERVICE_SETTINGS, change_setting, schema=CHANGE_SETTING_SCHEMA
    )

    # hass.services.register(
    #     DOMAIN, SERVICE_CAPTURE_IMAGE, capture_image, schema=CAPTURE_IMAGE_SCHEMA
    # )

    # hass.services.register(
    #     DOMAIN, SERVICE_TRIGGER_AUTOMATION, trigger_automation, schema=AUTOMATION_SCHEMA
    # )

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    hass.services.async_remove(DOMAIN, SERVICE_SETTINGS)
    # hass.services.async_remove(DOMAIN, SERVICE_CAPTURE_IMAGE)
    # hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_AUTOMATION)

    platforms = get_platforms(entry)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, platforms)
    
    if DOMAIN in hass.data and hass.data[DOMAIN]:
       hass.data[DOMAIN].logout_listener()
       hass.data.pop(DOMAIN)

    return unload_ok

@callback
def get_platforms(config_entry):
    """Return the platforms belonging to a config_entry."""
    return ["sensor","binary_sensor"]

async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    print('xxxxxxxxxxx update_listener')
    await hass.config_entries.async_reload(config_entry.entry_id)

def async_add_sensors(hass: HomeAssistant, async_add_entities: AddEntitiesCallback, validate_sensor_fn: any):
    ''' validate and add sensor for device '''
    sys: fwiot.FWIOTSystem = hass.data[DOMAIN]

    devices = []
    # Add all entities to HA
    for each in sys.devices:        

        if not sys.devices[each].inited:    
           devices.append(fwiot.FWIOTDeviceType(sys.devices[each]))
           devices.append(fwiot.FWIOTDeviceStatus(sys.devices[each]))
           devices.append(fwiot.FWIOTDeviceLastOnline(sys.devices[each]))
           sys.devices[each].inited = True

        validate_sensor_fn(sys.devices[each], devices)

    async_add_entities(devices)