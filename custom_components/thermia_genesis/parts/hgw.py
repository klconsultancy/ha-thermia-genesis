"""HGW, hot gas heat recovery (chapter 6.2): hot water from the compressor's hot gas."""

from ..descriptions import BinarySensor, Sensor, alarm, enabled_setting, signal, temperature

SENSORS: tuple[Sensor, ...] = (temperature("supply_line_temperature"),)

BINARY_SENSORS: tuple[BinarySensor, ...] = (
    enabled_setting("enable"),
    alarm("sensor_alarm"),
    signal("regulation_control_signal"),
)
