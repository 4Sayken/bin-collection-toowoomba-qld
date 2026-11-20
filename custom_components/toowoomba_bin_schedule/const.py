"""Constants for Toowoomba Bin Schedule."""

from datetime import timedelta

DOMAIN = "toowoomba_bin_schedule"
ATTRIBUTION = "Data provided by Toowoomba Regional Council"

CONF_ADDRESS = "address"
CONF_GREEN_SERVICE = "green_service"

UPDATE_INTERVAL = timedelta(hours=6)
