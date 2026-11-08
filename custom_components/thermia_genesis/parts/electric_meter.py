"""Electric meter (chapter 9): the current limiter's meter on the house connection."""

from homeassistant.components.sensor import SensorDeviceClass

from ..descriptions import BinarySensor, Sensor, enabled_setting, energy, measurement


def current(key: str) -> Sensor:
    """Describe a phase current in A."""
    return measurement(key, "A", SensorDeviceClass.CURRENT, precision=2)


def voltage(key: str) -> Sensor:
    """Describe a voltage in V."""
    return measurement(key, "V", SensorDeviceClass.VOLTAGE, precision=1)


def power(key: str) -> Sensor:
    """Describe a phase power in W; negative when the house exports."""
    return measurement(key, "W", SensorDeviceClass.POWER, precision=0, enabled=True)


SENSORS: tuple[Sensor, ...] = (
    current("l1_current"),
    current("l2_current"),
    current("l3_current"),
    voltage("l1_voltage"),
    voltage("l2_voltage"),
    voltage("l3_voltage"),
    voltage("l1_l2_voltage"),
    voltage("l2_l3_voltage"),
    voltage("l3_l1_voltage"),
    power("l1_power"),
    power("l2_power"),
    power("l3_power"),
    # The 32-bit total; the 16-bit meter value wraps after 65535 kWh (docs/design.md).
    energy("kwh_total", enabled=True),
    energy("meter_value"),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = (enabled_setting("enable_current_limitation"),)
