"""Mix valve 1 (chapter 5.2): a second heating circuit, optionally for passive cooling."""

from thermia_genesis.v17_1.enums import MixValveMode

from ..descriptions import (
    BinarySensor,
    Sensor,
    alarm,
    enabled_setting,
    enumeration,
    percentage,
    running,
    setting,
    temperature,
)

SENSORS: tuple[Sensor, ...] = (
    temperature("supply_line_temperature"),
    temperature("desired_temperature"),
    percentage("position"),
    # Settings
    enumeration("mode", MixValveMode, diagnostic=True),
    setting("min_limitation_set_point_curve", "°C", precision=1),
    setting("max_limitation_set_point_curve", "°C", precision=1),
    setting("curve_y_1", "°C", precision=1),
    setting("curve_y_2", "°C", precision=1),
    setting("curve_y_3", "°C", precision=1),
    setting("curve_y_4", "°C", precision=1),
    setting("curve_y_5", "°C", precision=1),
    setting("curve_y_6", "°C", precision=1),
    setting("curve_y_7", "°C", precision=1),
    setting("passive_cooling_supply_set_point", "°C", precision=1),
    setting("cooling_minimum_outdoor_temperature", "°C", precision=1),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = (
    # Settings
    enabled_setting("enable"),
    enabled_setting("enable_outdoor_temperature_dependent_cooling"),
    enabled_setting("enable_internal_brine_pump_when_cooling"),
    # Alarms
    alarm("supply_line_sensor_alarm"),
    alarm("supply_temperature_deviation_alarm"),
    # Running
    running("circulation_pump_control_signal"),
    running("producing_passive_cooling"),
)
