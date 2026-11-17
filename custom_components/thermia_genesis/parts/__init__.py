"""The entities of each part of the pump, one module per part."""

from typing import TYPE_CHECKING

from . import (
    cooling,
    electric_meter,
    energy_statistics,
    heat,
    heat_pump,
    hgw,
    mix_valve_1,
    pool,
    status,
    tap_water,
)

if TYPE_CHECKING:
    from ..descriptions import BinarySensor, Number, Select, Sensor

# The sensors and binary sensors of each part, by the part's attribute on ThermiaGenesis.
SENSORS: dict[str, tuple[Sensor, ...]] = {
    "cooling": cooling.SENSORS,
    "electric_meter": electric_meter.SENSORS,
    "energy_statistics": energy_statistics.SENSORS,
    "heat": heat.SENSORS,
    "heat_pump": heat_pump.SENSORS,
    "hgw": hgw.SENSORS,
    "mix_valve_1": mix_valve_1.SENSORS,
    "pool": pool.SENSORS,
    "status": status.SENSORS,
    "tap_water": tap_water.SENSORS,
}
BINARY_SENSORS: dict[str, tuple[BinarySensor, ...]] = {
    "cooling": cooling.BINARY_SENSORS,
    "electric_meter": electric_meter.BINARY_SENSORS,
    "heat": heat.BINARY_SENSORS,
    "heat_pump": heat_pump.BINARY_SENSORS,
    "hgw": hgw.BINARY_SENSORS,
    "mix_valve_1": mix_valve_1.BINARY_SENSORS,
    "pool": pool.BINARY_SENSORS,
    "status": status.BINARY_SENSORS,
    "tap_water": tap_water.BINARY_SENSORS,
}
SELECTS: dict[str, tuple[Select, ...]] = {
    "status": status.SELECTS,
}
NUMBERS: dict[str, tuple[Number, ...]] = {
    "heat_pump": heat_pump.NUMBERS,
    "tap_water": tap_water.NUMBERS,
}
