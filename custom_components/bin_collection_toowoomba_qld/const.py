"""Constants for Bin Collection Toowoomba QLD."""

DOMAIN = "bin_collection_toowoomba_qld"
ATTRIBUTION = "Data provided by Toowoomba Regional Council"

CONF_ADDRESS = "address"
CONF_GREEN_SERVICE = "green_service"

STORAGE_VERSION = 1

# The council is checked once a month, in the early morning of the 1st. Each
# property gets its own minute within this hour so installs don't all hit the
# council's site at once.
CHECK_HOUR = 4
