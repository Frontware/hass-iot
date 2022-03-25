"""Support for the FWIOT devices."""
from __future__ import annotations

import logging
import voluptuous as vol

from functools import partial
from requests.exceptions import ConnectTimeout, HTTPError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_DATE,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_TIME,
    CONF_PASSWORD,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import Event, HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, entity
from homeassistant.helpers.dispatcher import dispatcher_send

from .const import ATTRIBUTION, CONF_POLLING, DEFAULT_CACHEDB, DOMAIN, LOGGER
from .fwiot import FWIOTSystem, FWIOTAuto, FWIOTDev

_LOGGER = logging.getLogger(__name__)

SERVICE_SETTINGS = "change_setting"
SERVICE_CAPTURE_IMAGE = "capture_image"
SERVICE_TRIGGER_AUTOMATION = "trigger_automation"

ATTR_DEVICE_NAME = "device_name"
ATTR_DEVICE_TYPE = "device_type"
ATTR_EVENT_CODE = "event_code"
ATTR_EVENT_NAME = "event_name"
ATTR_EVENT_TYPE = "event_type"
ATTR_EVENT_UTC = "event_utc"
ATTR_SETTING = "setting"
ATTR_USER_NAME = "user_name"
ATTR_APP_TYPE = "app_type"
ATTR_EVENT_BY = "event_by"
ATTR_VALUE = "value"

CONFIG_SCHEMA = cv.removed(DOMAIN, raise_if_present=False)

CHANGE_SETTING_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SETTING): cv.string, vol.Required(ATTR_VALUE): cv.string}
)

CAPTURE_IMAGE_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})

AUTOMATION_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})

PLATFORMS = [
    Platform.BINARY_SENSOR,
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info('async_setup_entry')
    """Set up FWIOT integration from a config entry."""
    username = entry.data[CONF_USERNAME]
    password = entry.data[CONF_PASSWORD]
    polling = entry.data[CONF_POLLING]
    cache = hass.config.path(DEFAULT_CACHEDB)

    # For previous config entries where unique_id is None
    if entry.unique_id is None:
        hass.config_entries.async_update_entry(
            entry, unique_id=entry.data[CONF_USERNAME]
        )

    try:
        FWIOT = await hass.async_add_executor_job(
            FWIOT, username, password, True, True, True, cache
        )

    except Exception as ex:
        raise ConfigEntryAuthFailed(f"{ex}") from ex

    hass.data[DOMAIN] = FWIOTSystem(polling)

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    await setup_hass_events(hass)
    await hass.async_add_executor_job(setup_hass_services, hass)
    
    _LOGGER.info('async_setup_entry done')
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.info('async_unload_entry')
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_SETTINGS)
    hass.services.async_remove(DOMAIN, SERVICE_CAPTURE_IMAGE)
    hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_AUTOMATION)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    await hass.async_add_executor_job(hass.data[DOMAIN].FWIOT.events.stop)
    await hass.async_add_executor_job(hass.data[DOMAIN].FWIOT.logout)

    hass.data[DOMAIN].logout_listener()
    hass.data.pop(DOMAIN)

    _LOGGER.info('async_unload_entry done')
    return unload_ok


def setup_hass_services(hass: HomeAssistant) -> None:
    """Home Assistant services."""
    _LOGGER.info('setup_hass_services')

    def change_setting(call: ServiceCall) -> None:
        """Change an FWIOT system setting."""
        setting = call.data[ATTR_SETTING]
        value = call.data[ATTR_VALUE]

        try:
            hass.data[DOMAIN].FWIOT.set_setting(setting, value)
        except Exception as ex:
            LOGGER.warning(ex)

    hass.services.register(
        DOMAIN, SERVICE_SETTINGS, change_setting, schema=CHANGE_SETTING_SCHEMA
    )
    _LOGGER.info('setup_hass_services done')

async def setup_hass_events(hass: HomeAssistant) -> None:
    """Home Assistant start and stop callbacks."""
    _LOGGER.info('setup_hass_events')

    def logout(event: Event) -> None:
        """Logout of FWIOT."""
        if not hass.data[DOMAIN].polling:
            hass.data[DOMAIN].FWIOT.events.stop()

        hass.data[DOMAIN].FWIOT.logout()
        LOGGER.info("Logged out of FWIOT")

    if not hass.data[DOMAIN].polling:
        await hass.async_add_executor_job(hass.data[DOMAIN].FWIOT.events.start)

    hass.data[DOMAIN].logout_listener = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, logout
    )
    _LOGGER.info('setup_hass_events done')

class FWIOTEntity(entity.Entity):
    """Representation of an FWIOT entity."""

    _attr_attribution = ATTRIBUTION

    def __init__(self, data: FWIOTSystem) -> None:
        _LOGGER.info('FWIOTEntity init')
        """Initialize FWIOT entity."""
        self._data = data
        self._attr_should_poll = data.polling

    async def async_added_to_hass(self) -> None:
        """Subscribe to FWIOT connection status updates."""
        await self.hass.async_add_executor_job(
            self._data.FWIOT.events.add_connection_status_callback,
            self.unique_id,
            self._update_connection_status,
        )

        self.hass.data[DOMAIN].entity_ids.add(self.entity_id)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from FWIOT connection status updates."""
        await self.hass.async_add_executor_job(
            self._data.FWIOT.events.remove_connection_status_callback, self.unique_id
        )

    def _update_connection_status(self) -> None:
        """Update the entity available property."""
        self._attr_available = self._data.FWIOT.events.connected
        self.schedule_update_ha_state()


class FWIOTDevice(FWIOTEntity):
    """Representation of an FWIOT device."""

    def __init__(self, data: FWIOTSystem, device: FWIOTDev) -> None:
        _LOGGER.info('FWIOTDevice init')
        """Initialize FWIOT device."""
        super().__init__(data)
        self._device = device
        self._attr_name = device.name
        self._attr_unique_id = device.device_uuid

    async def async_added_to_hass(self) -> None:
        """Subscribe to device events."""
        await super().async_added_to_hass()
        await self.hass.async_add_executor_job(
            self._data.FWIOT.events.add_device_callback,
            self._device.device_id,
            self._update_callback,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from device events."""
        await super().async_will_remove_from_hass()
        await self.hass.async_add_executor_job(
            self._data.FWIOT.events.remove_all_device_callbacks, self._device.device_id
        )

    def update(self) -> None:
        """Update device state."""
        self._device.refresh()

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return the state attributes."""
        return {
            "device_id": self._device.device_id,
            "battery_low": self._device.battery_low,
            "no_response": self._device.no_response,
            "device_type": self._device.type,
        }

    @property
    def device_info(self) -> entity.DeviceInfo:
        """Return device registry information for this entity."""
        return entity.DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            manufacturer="FWIOT",
            model=self._device.type,
            name=self._device.name,
        )

    def _update_callback(self, device: FWIOTDev) -> None:
        """Update the device state."""
        self.schedule_update_ha_state()


class FWIOTAutomation(FWIOTEntity):
    """Representation of an FWIOT automation."""

    def __init__(self, data: FWIOTSystem, automation: FWIOTAuto) -> None:
        _LOGGER.info('FWIOTAutomation init')
        """Initialize for FWIOT automation."""
        super().__init__(data)
        self._automation = automation
        self._attr_name = automation.name
        self._attr_unique_id = automation.automation_id
        self._attr_extra_state_attributes = {
            "type": "CUE automation",
        }

    def update(self) -> None:
        """Update automation state."""
        self._automation.refresh()
