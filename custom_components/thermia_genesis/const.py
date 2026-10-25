"""Constants of the Thermia Genesis integration."""

DOMAIN = "thermia_genesis"

CONF_UNIT_ID = "unit_id"

DEFAULT_PORT = 502
# The Genesis controller ignores the unit id on Modbus TCP.
DEFAULT_UNIT_ID = 1

MANUFACTURER = "Thermia"
# There is no register for the model; the user renames the device.
MODEL = "Genesis"

# The pump's parts, by their attribute on ThermiaGenesis; each one present gets a device.
# Status belongs to the pump itself.
PARTS = (
    "heat_pump",
    "heat",
    "mix_valve_1",
    "tap_water",
    "hgw",
    "cooling",
    "pool",
    "electric_meter",
)
