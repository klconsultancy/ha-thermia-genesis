"""Pool (chapter 8): heating a pool through its own heat exchanger."""

from ..descriptions import (
    BinarySensor,
    Sensor,
    alarm,
    enabled_setting,
    measurement,
    setting,
    signal,
    temperature,
)

SENSORS: tuple[Sensor, ...] = (
    temperature("supply_line_temperature"),
    temperature("return_line_temperature"),
    measurement("desired_gear", precision=0),
    # Settings
    setting("charge_set_point", "°C", precision=1),
    setting("return_temperature_to_heat_exchanger_set_point", "°C", precision=1),
    setting("hysteresis_set_point", "K", precision=1),
    setting("gear_shift_delay", "s"),
    setting("minimum_allowed_gear"),
    setting("maximum_allowed_gear"),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = (
    # Settings
    enabled_setting("enable_pool"),
    enabled_setting("enable_external_additional_heater"),
    # Alarms
    alarm("return_line_sensor_alarm"),
    # Signals
    signal("external_stop"),
    signal("directional_valve_position"),
)
