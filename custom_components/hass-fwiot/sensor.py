"""Platform for sensor integration."""
from __future__ import annotations

import datetime 
import pytz
import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import (
    DEVICE_CLASS_TIMESTAMP,
    TEMP_CELSIUS,
    PERCENTAGE
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from .const import DEVICE_FINGER, DOMAIN, DEVICE_EMPDETECTOR, DEVICE_THERMIDITY
from . import async_add_sensors
from .fwiot import FWIOTDevice, FWIOTEntity

# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_sensors(hass, async_add_entities, add_sensor_fn)

def add_sensor_fn(device, rets):
    ''' add sensors for employee detector '''

    if device.type == DEVICE_EMPDETECTOR:
       rets.append(FWIOTEmployeeUpdate(device))
       rets.append(FWIOTEmployeeName(device))
    elif device.type == DEVICE_THERMIDITY:
       rets.append(FWIOTTemperature(device))
       rets.append(FWIOTHumudity(device))
    elif device.type == DEVICE_FINGER:
        rets.append(FWBiometricLastCrawl(device))
        for each in device._raw.get('emps', {}):
            n = device._raw.get('emps', {})[each]
            if n:
               rets.append(FWBiometricEmployeeName(device, n, each))

class FWIOTEmployeeUpdate(FWIOTEntity):
    
    device_class = DEVICE_CLASS_TIMESTAMP

    """A employee detector implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_update"
        self._attr_name = "employee time detect"
        self._tdetected = None

    @property
    def state(self):
        """Return"""
        return datetime.datetime.fromtimestamp(self._tdetected,tz=pytz.UTC) if self._tdetected else None

    async def async_update(self):
        self._tdetected = self.coordinator.data.get('data', {}).get('ts', False)

class FWIOTEmployeeName(FWIOTEntity):
    
    """A employee detector implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_emp"
        self._attr_name = "employee name detect"
        self._edetected = None

    @property
    def state(self):
        """Return"""
        return self._edetected

    async def async_update(self):
        self._edetected = self.coordinator.data.get('data', {}).get('employee', '-')

    @property
    def icon(self):
        return 'mdi:account-question'

class FWIOTTemperature(FWIOTEntity):
    """Representation of a Sensor."""

    _attr_name = "Temperature"
    _attr_native_unit_of_measurement = TEMP_CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_temp"
        self._temp = 0

    @property
    def unit_of_measurement(self):
        return TEMP_CELSIUS

    @property
    def state(self):
        """Return"""
        return self._temp

    async def async_update(self):
        self._temp = self.coordinator.data.get('data', {}).get('temp', 0)

class FWIOTHumudity(FWIOTEntity):
    """Representation of a Sensor."""

    _attr_name = "Humudity"
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_humid"
        self._hum = 0

    @property
    def unit_of_measurement(self):
        return PERCENTAGE

    @property
    def state(self):
        """Return"""
        return self._hum

    async def async_update(self):        
        self._hum = self.coordinator.data.get('data', {}).get('hum', 0)

class FWBiometricEmployeeName(FWIOTEntity):

    device_class = DEVICE_CLASS_TIMESTAMP

    """A fingerprint implementation for device."""
    def __init__(self, device: FWIOTDevice, emp: str, empid: str) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_b_{empid}"
        self._attr_name = f" {emp}"
        self._emp = emp
        self._last = 0

    @property
    def state(self):
        """Return"""
        return datetime.datetime.fromtimestamp(self._last,tz=pytz.UTC) if self._last else None

    async def async_update(self):
        if not self.coordinator.data.get(self._emp, {}):
           return
        # get local timezone
        self._last = pytz.timezone( self._device._tz or 'Asia/Bangkok').localize(
            datetime.datetime.strptime(self.coordinator.data.get(self._emp, {}), '%d/%m/%Y %H:%M:%S'),is_dst=None
        ).astimezone(pytz.utc).timestamp()

class FWBiometricLastCrawl(FWIOTEntity):

    device_class = DEVICE_CLASS_TIMESTAMP

    """A fingerprint implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_last_c"
        self._attr_name = "last connect"

    @property
    def state(self):
        """Return"""
        return datetime.datetime.fromtimestamp(self._device._last_connect,tz=pytz.UTC) if self._device._last_connect else None

    async def async_update(self):
        pass