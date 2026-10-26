"""Hot water (chapter 6.1), which the library calls tap water."""

from ..descriptions import (
    BinarySensor,
    Sensor,
    alarm,
    enabled_setting,
    measurement,
    operating_hours,
    percentage,
    setting,
    temperature,
)

SENSORS: tuple[Sensor, ...] = (
    temperature("top_temperature", enabled=True),
    temperature("lower_temperature"),
    temperature("weighted_temperature"),
    percentage("valve_position"),
    operating_hours("operating_hours"),
    measurement("desired_gear", precision=0),
    # Settings
    setting("start_temperature", "°C", precision=1),
    setting("stop_temperature", "°C", precision=1),
    setting("maximum_allowed_gear"),
    setting("minimum_allowed_gear"),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = (
    # Settings
    enabled_setting("enable_hot_gas_pump"),
    # Alarms
    alarm("mid_sensor_alarm"),
)
