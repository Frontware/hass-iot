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
    DEVICE_CLASS_TIMESTAMP
)

from .const import DOMAIN
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

    if device.type == 'EMPDETECTOR':
       rets.append(FWIOTEmployeeUpdate(device))
       rets.append(FWIOTEmployeeName(device))

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