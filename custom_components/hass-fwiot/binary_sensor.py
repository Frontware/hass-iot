"""Platform for sensor integration."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from . import async_add_sensors
from .fwiot import FWIOTDevice, FWIOTEntity, FWIOTSystem

# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_sensors(hass, async_add_entities, add_sensor_fn)

def add_sensor_fn(device, rets):
    ''' add sensors for binary detector '''

    rets.append(FWIOTDeviceActive(device))
    rets.append(FWIOTDeviceLock(device))      

    if device.type == 'EMPDETECTOR':
       rets.append(FWIOTEmployeeFound(device))  

class FWIOTDeviceActive(FWIOTEntity, BinarySensorEntity):
    """A device active implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_active"
        self._attr_name = "device active"

    @property
    def is_on(self) -> bool:
        return self._device.active

    async def async_update(self):
        print('async_update')

class FWIOTDeviceLock(FWIOTEntity, BinarySensorEntity):
    """A device lock implementation for device."""
    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_locked"
        self._attr_name = "device locked"

    @property
    def is_on(self) -> bool:
        return self._device.locked

    async def async_update(self):
        print('async_update')                

    @property
    def icon(self):
        return 'mdi:lock' if self._device.locked else 'mdi:lock-open'

class FWIOTEmployeeFound(FWIOTEntity, BinarySensorEntity):
    """A binary sensor implementation for device."""

    def __init__(self, device: FWIOTDevice) -> None:
        super().__init__(device)
        self._attr_unique_id = f"{self._device.unique_id}_detect"
        self._attr_name = "employee detect"
        self._found = False

    @property
    def is_on(self) -> bool:
        """Return True if the binary sensor is on."""
        return self._found  

    async def async_update(self):
        self._found = self.coordinator.data.get('data', {}).get('detected', False)
    
    @property
    def icon(self):
        return 'mdi:brightness-1' if self._found else 'mdi:block-helper'

    @property
    def icon_color(self):        
        return 'green' if self._found else 'red'