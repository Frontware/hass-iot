import requests
import json
import datetime
import pytz
import aiohttp
import asyncio
from typing import Any
from datetime import timedelta
import async_timeout

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from homeassistant.const import (
    DEVICE_CLASS_TIMESTAMP
)
from homeassistant.helpers.aiohttp_client import (
    async_aiohttp_proxy_web,
    async_get_clientsession,
)
from .const import DOMAIN, LOGGER

class FWIOTDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching AccuWeather data API."""

    def __init__(
        self,
        hass: HomeAssistant,
        device: any
    ) -> None:
        self._hass = hass
        self._device = device
        """Initialize."""
        # Enabling the forecast download increases the number of requests per data
        # update, we use 40 minutes for current condition only and 80 minutes for
        # current condition and forecast as update interval to not exceed allowed number
        # of requests. We have 50 requests allowed per day, so we use 36 and leave 14 as
        # a reserve for restarting HA.
        update_interval = timedelta(seconds=10)
        print("Data will be update every %s", update_interval)

        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=update_interval)

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        url = 'https://iot.frontware.com/json/%s.json?lastid=20&limit=20' % self._device._key
        
        websession = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(10):
                response = await websession.get(url)

                if response.status != 200:
                   raise Exception('status code not 200') 

                rets = await response.json()
                ret = {}
                if type(rets) is list:
                   for each in rets:
                       if each.get('data', False):
                          try: 
                             dd = json.loads(each.get('data')) 
                          except:
                             dd = {}  
                          print(dd)  
                          if dd.get('status', False) and not ret.get('status',False):
                             ret['status'] = dd
                          elif dd and  not ret.get('data',False):
                             ret['data'] = dd
                          
                          if ret.get('status',False) and ret.get('data',False):
                             break                    

                return ret

        except asyncio.TimeoutError:
            LOGGER.error("Timeout getting camera image from %s", self.name)

        except aiohttp.ClientError as err:
            LOGGER.error("Error getting new camera image from %s: %s", self.name, err)

class FWIOTSystem:
    """System class."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the system."""
        self._hass = hass
        self.logout_listener = None
        '''
        hass logout listener
        '''
        self.devices = {}
        ''' serial devices '''

    def get_device(self, api_key):
        ''' get device status '''
        
        url = 'https://iot.frontware.com/status/%s' % api_key
        r = requests.get(url)

        if r.status_code != 200:
           return Exception('Error connect: code %s' % r.status_code)

        rr = json.loads(r.content)

        if api_key in self.devices:
           return Exception('Serial already exist')

        self.devices[rr.get('serial')] = FWIOTDevice(self, rr, api_key)
        return rr.get('serial')

class FWIOTDevice:
    def __init__(self, sys: FWIOTSystem, device: any, api_key: any) -> None:
        self._sys = sys
        self._raw = device
        self._key = api_key
        self._attr_name = device.get('token','')
        self._attr_unique_id = f"dv-{device.get('serial','')}"
        self.coordinator = None
        self._type = device.get('device_type_code')
        self._typename = device.get('device_type_name')
        self.inited = False

    @property
    def type(self):
        return self._type

    @property
    def type_name(self):
        return self._typename

    @property
    def unique_id(self):
        return self._attr_unique_id
    @property
    def name(self):
        return self._attr_name

    @property
    def model(self):
        return self._raw.get('device_type_name','')

    @property
    def version(self):
        return self._raw.get('version','')

    @property
    def active(self):
        return self._raw.get('active',False)

    @property
    def locked(self):
        return self._raw.get('locked',False)

    @property
    def status(self):
        return self._raw.get('status','')

    @property
    def last_online(self):
        return self._raw.get('last_online', '')

class FWIOTEntity(CoordinatorEntity, Entity):
    """FWIOT entity."""
    coordinator: FWIOTDataUpdateCoordinator

    def __init__(self, device: FWIOTDevice):
        """Initialize the entity."""
        super().__init__(device.coordinator)
        self._device = device
        #self.async_change = fwiot.coordinator["async_change"]

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        print('FWIOTEntity.async_added_to_hass')

    async def async_will_remove_from_hass(self) -> None:
        print('FWIOTEntity.async_will_remove_from_hass')

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this entity."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device.unique_id)},
            manufacturer="Frontware IOT",
            model=self._device.model,
            name=self._device.name,
            sw_version=self._device.version
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        
        print('handle_coordinator_update')
        self.async_write_ha_state()


class FWIOTDeviceStatus(FWIOTEntity):
    """A device status implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_status"
        self._attr_name = "device's status"

    @property
    def state(self):
        """Return"""
        return f"{self._device.status}"

    async def async_update(self):
        if self.coordinator.data.get('status', False):
           self._device._raw['status'] = self.coordinator.data.get('status', {}).get('status')
        self.async_write_ha_state()   

    @property
    def icon(self):
        return 'mdi:cloud-check-outline' if self._device.status == "Online" else 'mdi:cloud-off-outline'

class FWIOTDeviceLastOnline(FWIOTEntity):

    device_class = DEVICE_CLASS_TIMESTAMP

    """A device last online implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_laston"
        self._attr_name = "device's last online"

    @property
    def state(self):
        """Return"""
        return datetime.datetime.fromtimestamp(self._device.last_online,tz=pytz.UTC) if self._device.last_online else None

    async def async_update(self):
        self._device._raw['last_online'] = self.coordinator.data.get('status', {}).get('ts', False)
        self.async_write_ha_state()

class FWIOTDeviceType(FWIOTEntity):
    """A device type implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_type"
        self._attr_name = "device's type"

    @property
    def state(self):
        """Return"""
        return f"{self._device.type_name}"

    @property
    def icon(self):
        return 'mdi:cast-audio-variant'