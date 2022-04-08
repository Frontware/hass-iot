"""Constants for the Abode Security System component."""
import logging
from datetime import timedelta
import voluptuous as vol

from homeassistant.helpers import config_validation as cv, entity
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

LOGGER = logging.getLogger(__package__)

DOMAIN = "hass_fwiot"
ATTRIBUTION = "provided by iot.frontware.com"

DEFAULT_CACHEDB = "fwiot_cache.pickle"
CONF_POLLING = "polling"

UPDATE_INTERVAL = timedelta(seconds=15)
POLLING_TIMEOUT_SEC = 10

DEVICE_FINGER = 'FINGER'
DEVICE_EMPDETECTOR = 'EMPDETECTOR'
DEVICE_THERMIDITY = 'THERMIDITY'

DEVICES_READY = [DEVICE_EMPDETECTOR, DEVICE_THERMIDITY]

DEVICES_ICON = {
    DEVICE_FINGER: 'mdi:fingerprint',
    DEVICE_EMPDETECTOR: 'mdi:motion-sensor',
    DEVICE_THERMIDITY: 'mdi:thermometer-lines',
}

# Keys
KEY_COORDINATOR = "coordinator"
KEY_DEVICE = "device"

FLOWTYPE_IOT = "IOT device"
FLOWTYPE_FINGER = "Fingerprint"

FIELD_TYPE ="type"
FIELD_API ="api_key"
FIELD_IP ="finger_print_ip"
FIELD_PORT ="finger_print_port"

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

SERVICE_SETTINGS = "change_setting"
SERVICE_CAPTURE_IMAGE = "capture_image"
SERVICE_TRIGGER_AUTOMATION = "trigger_automation"


CHANGE_SETTING_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SETTING): cv.string, vol.Required(ATTR_VALUE): cv.string}
)

CAPTURE_IMAGE_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})

AUTOMATION_SCHEMA = vol.Schema({ATTR_ENTITY_ID: cv.entity_ids})