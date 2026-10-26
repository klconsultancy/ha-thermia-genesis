"""The entities of each part of the pump, one module per part."""

from typing import TYPE_CHECKING

from . import heat_pump, status

if TYPE_CHECKING:
    from ..descriptions import BinarySensor, Sensor

# The sensors and binary sensors of each part, by the part's attribute on ThermiaGenesis.
SENSORS: dict[str, tuple[Sensor, ...]] = {
    "heat_pump": heat_pump.SENSORS,
    "status": status.SENSORS,
}
BINARY_SENSORS: dict[str, tuple[BinarySensor, ...]] = {
    "heat_pump": heat_pump.BINARY_SENSORS,
    "status": status.BINARY_SENSORS,
}
