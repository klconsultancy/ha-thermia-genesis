"""Cooling (chapter 7): active and passive cooling, with the cooling circuit's mix valve."""

from ..descriptions import (
    BinarySensor,
    Sensor,
    alarm,
    enabled_setting,
    measurement,
    percentage,
    running,
    setting,
    signal,
    temperature,
)

SENSORS: tuple[Sensor, ...] = (
    temperature("circuit_supply_line_temperature"),
    percentage("mix_valve_opening_degree"),
    measurement("desired_gear", precision=0),
    # Settings
    setting("start_temperature", "°C", precision=1),
    setting("stop_temperature", "°C", precision=1),
    setting("gear_shift_delay", "s"),
    setting("minimum_allowed_gear"),
    setting("maximum_allowed_gear"),
    setting("mix_valve_set_point", "°C", precision=1),
    setting("supply_line_mix_valve_lowest_allowed_opening_degree", "%", precision=0),
    setting("supply_line_mix_valve_highest_allowed_opening_degree", "%", precision=0),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = (
    # Settings
    enabled_setting("enable_active_cooling"),
    enabled_setting("enable_passive_cooling"),
    # Alarms
    alarm("supply_line_sensor_alarm"),
    alarm("circuit_supply_line_temperature_deviation_alarm"),
    # Running
    running("circuit_circulation_pump_control_signal"),
    # Signals
    signal("external_start_brine_pump"),
    signal("circuit_regulation_control_signal"),
    signal("surplus_heat_directional_valve_position"),
    signal("active_cooling_directional_valve_position"),
)
