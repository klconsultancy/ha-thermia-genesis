"""The entity descriptions and the helpers the parts declare their entities with."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntityDescription
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)

from .entity import ThermiaGenesisEntityDescription

if TYPE_CHECKING:
    from enum import Enum, IntFlag

# Home Assistant's unit for each unit the library declares.
UNITS: dict[str | None, str] = {
    "°C": UnitOfTemperature.CELSIUS,
    "K": UnitOfTemperature.KELVIN,
    "%": PERCENTAGE,
    "rpm": REVOLUTIONS_PER_MINUTE,
    "h": UnitOfTime.HOURS,
    "s": UnitOfTime.SECONDS,
    "bar(g)": UnitOfPressure.BAR,
    "A": UnitOfElectricCurrent.AMPERE,
    "V": UnitOfElectricPotential.VOLT,
    "W": UnitOfPower.WATT,
    "kW": UnitOfPower.KILO_WATT,
    "kWh": UnitOfEnergy.KILO_WATT_HOUR,
}

# The device class of a setting, by its unit; a measurement says its own.
SETTING_CLASSES: dict[str, SensorDeviceClass] = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "K": SensorDeviceClass.TEMPERATURE_DELTA,
    "s": SensorDeviceClass.DURATION,
    "A": SensorDeviceClass.CURRENT,
    "kW": SensorDeviceClass.POWER,
}


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisSensorEntityDescription(
    ThermiaGenesisEntityDescription, SensorEntityDescription
):
    """A sensor for one field of a part."""


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisBinarySensorEntityDescription(
    ThermiaGenesisEntityDescription, BinarySensorEntityDescription
):
    """A binary sensor for a bit of a part, or for one member of a flags field."""

    member: IntFlag | None = None


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisSelectEntityDescription(
    ThermiaGenesisEntityDescription, SelectEntityDescription
):
    """A select for a writable enum field; its options come from the library's validator."""


type Sensor = ThermiaGenesisSensorEntityDescription
type BinarySensor = ThermiaGenesisBinarySensorEntityDescription
type Select = ThermiaGenesisSelectEntityDescription


def measurement(  # noqa: PLR0913
    key: str,
    unit: str | None = None,
    device_class: SensorDeviceClass | None = None,
    *,
    precision: int | None = None,
    enabled: bool = False,
    diagnostic: bool = False,
) -> Sensor:
    """Describe a value the pump measures or calculates."""
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=None if unit is None else UNITS[unit],
        device_class=device_class,
        # A diagnostic value (a count, a version) has no use in the long-term statistics.
        state_class=None if diagnostic else SensorStateClass.MEASUREMENT,
        suggested_display_precision=precision,
        entity_registry_enabled_default=enabled,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


def temperature(key: str, *, enabled: bool = False) -> Sensor:
    """Describe a measured temperature in °C."""
    return measurement(key, "°C", SensorDeviceClass.TEMPERATURE, precision=1, enabled=enabled)


def power(key: str, *, enabled: bool = False) -> Sensor:
    """Describe a power the pump reports in kW, shown in W like the other power sensors.

    Home Assistant's history draws one graph per unit, so a P1 meter in W and the pump in
    kW would land in separate graphs.
    """
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_registry_enabled_default=enabled,
    )


def temperature_delta(key: str) -> Sensor:
    """Describe a temperature difference in K."""
    return measurement(key, "K", SensorDeviceClass.TEMPERATURE_DELTA, precision=1)


def percentage(key: str, *, enabled: bool = False) -> Sensor:
    """Describe a speed, opening or demand in %."""
    return measurement(key, "%", precision=0, enabled=enabled)


def operating_hours(key: str, *, enabled: bool = False) -> Sensor:
    """Describe a counter of hours that only goes up."""
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=enabled,
    )


def meter_energy(key: str) -> Sensor:
    """Describe a meter's energy in kWh that never goes down; disabled by default.

    Only for counters that never go down: total_increasing reads any drop as a reset.
    """
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    )


def enumeration(
    key: str, enum: type[Enum], *, enabled: bool = False, diagnostic: bool = False
) -> Sensor:
    """Describe an enum, shown as its lowercase member name."""
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENUM,
        options=[member.name.lower() for member in enum],
        entity_registry_enabled_default=enabled,
        entity_category=EntityCategory.DIAGNOSTIC if diagnostic else None,
    )


def setting(key: str, unit: str | None = None, *, precision: int | None = None) -> Sensor:
    """Describe a holding register: a setting, read-only until the write API."""
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=None if unit is None else UNITS[unit],
        device_class=None if unit is None else SETTING_CLASSES.get(unit),
        suggested_display_precision=precision,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def enabled_setting(key: str) -> BinarySensor:
    """Describe a coil: a setting that turns something on or off."""
    return ThermiaGenesisBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def alarm(key: str) -> BinarySensor:
    """Describe an alarm input; the aggregate alarm is the one to watch."""
    return ThermiaGenesisBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    )


def running(key: str, *, enabled: bool = False) -> BinarySensor:
    """Describe whether a compressor, pump or heater runs."""
    return ThermiaGenesisBinarySensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_registry_enabled_default=enabled,
    )


def signal(key: str) -> BinarySensor:
    """Describe any other bit the pump reports."""
    return ThermiaGenesisBinarySensorEntityDescription(
        key=key, translation_key=key, entity_registry_enabled_default=False
    )


def members(field: str, flags: type[IntFlag]) -> tuple[BinarySensor, ...]:
    """Describe one binary sensor per member of a flags field, disabled by default."""
    return tuple(
        ThermiaGenesisBinarySensorEntityDescription(
            key=f"{field}_{member.name.lower()}",  # type: ignore[union-attr]
            translation_key=f"{field}_{member.name.lower()}",  # type: ignore[union-attr]
            field=field,
            member=member,
            entity_registry_enabled_default=False,
        )
        for member in flags
    )


def choice(key: str, *, enabled: bool = False) -> Select:
    """Describe a writable enum setting, shown as its lowercase member name.

    Category config keeps it off the generated dashboard, where a mode such as Off would be
    a tap away; it shows among the device's controls.
    """
    return ThermiaGenesisSelectEntityDescription(
        key=key,
        translation_key=key,
        entity_registry_enabled_default=enabled,
        entity_category=EntityCategory.CONFIG,
    )
