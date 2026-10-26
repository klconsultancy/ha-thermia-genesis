"""The heating system (chapter 5.1): supply line, heat curve and buffer tank."""

from homeassistant.components.sensor import SensorDeviceClass

from ..descriptions import (
    BinarySensor,
    Sensor,
    alarm,
    enabled_setting,
    measurement,
    running,
    setting,
    signal,
    temperature,
)


def curve_point(key: str) -> Sensor:
    """Describe an outdoor temperature on the heat curve's x axis, which the pump fixes."""
    return measurement(key, "°C", SensorDeviceClass.TEMPERATURE, precision=1, diagnostic=True)


SENSORS: tuple[Sensor, ...] = (
    # System supply and return
    temperature("system_supply_line_temperature"),
    temperature("system_supply_line_calculated_set_point"),
    temperature("system_return_line_temperature"),
    measurement("calculated_demand", precision=2),
    measurement("desired_gear", precision=0),
    # Heat curve
    temperature("selected_heat_curve_supply_line"),
    curve_point("heat_curve_x_1"),
    curve_point("heat_curve_x_2"),
    curve_point("heat_curve_x_3"),
    curve_point("heat_curve_x_4"),
    curve_point("heat_curve_x_5"),
    curve_point("heat_curve_x_6"),
    curve_point("heat_curve_x_7"),
    # Buffer tank
    temperature("buffer_tank_temperature"),
    temperature("buffer_tank_charge_set_point"),
    # Settings
    setting("max_limitation_set_point_curve", "°C", precision=1),
    setting("min_limitation_set_point_curve", "°C", precision=1),
    setting("comfort_wheel_setting", "°C", precision=1),
    setting("heating_season_stop_temperature", "°C", precision=1),
    setting("fixed_system_supply_set_point", "°C", precision=1),
    setting("heat_curve_y_1", "°C", precision=1),
    setting("heat_curve_y_2", "°C", precision=1),
    setting("heat_curve_y_3", "°C", precision=1),
    setting("heat_curve_y_4", "°C", precision=1),
    setting("heat_curve_y_5", "°C", precision=1),
    setting("heat_curve_y_6", "°C", precision=1),
    setting("heat_curve_y_7", "°C", precision=1),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = (
    # Settings
    enabled_setting("enable_fixed_system_supply_set_point"),
    # Alarms
    alarm("system_supply_low_temperature_alarm"),
    alarm("system_supply_line_sensor_alarm"),
    alarm("room_temperature_sensor_alarm"),
    # Running
    running("system_circulation_pump_control_signal"),
    # Signals
    signal("heating_season_active"),
)
