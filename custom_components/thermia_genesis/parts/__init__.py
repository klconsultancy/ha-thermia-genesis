"""The entities of each part of the pump, one module per part."""

from typing import TYPE_CHECKING

from . import heat, heat_pump, hgw, mix_valve_1, status, tap_water

if TYPE_CHECKING:
    from ..descriptions import BinarySensor, Sensor

# The sensors and binary sensors of each part, by the part's attribute on ThermiaGenesis.
SENSORS: dict[str, tuple[Sensor, ...]] = {
    "heat": heat.SENSORS,
    "heat_pump": heat_pump.SENSORS,
    "hgw": hgw.SENSORS,
    "mix_valve_1": mix_valve_1.SENSORS,
    "status": status.SENSORS,
    "tap_water": tap_water.SENSORS,
}
BINARY_SENSORS: dict[str, tuple[BinarySensor, ...]] = {
    "heat": heat.BINARY_SENSORS,
    "heat_pump": heat_pump.BINARY_SENSORS,
    "hgw": hgw.BINARY_SENSORS,
    "mix_valve_1": mix_valve_1.BINARY_SENSORS,
    "status": status.BINARY_SENSORS,
    "tap_water": tap_water.BINARY_SENSORS,
}
