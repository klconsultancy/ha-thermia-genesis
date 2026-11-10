"""Climates: the heating circuit and the hot water, each with its set points and on or off."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityDescription
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from thermia_genesis.subsystem import Between
from thermia_genesis.v17_1.enums import RunningDemands
from thermia_genesis.v17_1.heat import Heat
from thermia_genesis.v17_1.heat_pump_unit import HeatPumpUnit
from thermia_genesis.v17_1.tap_water import TapWater

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator
from .entity import GROUPS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from thermia_genesis.subsystem import Field

    from .coordinator import ThermiaGenesisConfigEntry

# Coordinator-based, so no updates of its own; one write at a time.
PARALLEL_UPDATES = 1

# The fields each climate stands for, by part; they have no sensor (docs/design.md).
FIELDS: dict[str, set[str]] = {
    "heat": {"comfort_wheel_setting"},
    "heat_pump": {"enable_heat", "enable_tap_water"},
    "tap_water": {"start_temperature", "stop_temperature"},
}

# The step the card offers; the registers themselves take 0.01.
TARGET_STEP = 0.5


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the heating and the hot water climates."""
    coordinator = entry.runtime_data
    async_add_entities([ThermiaGenesisHeating(coordinator), ThermiaGenesisHotWater(coordinator)])


def to_register(field: Field[float], value: float) -> float:
    """Round ``value`` to ``field``'s resolution; Home Assistant converts °F without rounding."""
    resolution = field.resolution or 1
    return round(round(value / resolution) * resolution, 6)


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisClimateEntityDescription(ClimateEntityDescription):
    """A circuit: its part, the coil that turns it on and what heats it."""

    # The heat pump unit's coil that turns the circuit on.
    enable: Field[bool]
    # A set point, whose validator gives the range of every set point.
    set_point: Field[float]
    # The running demands that heat the circuit.
    heating: RunningDemands


class ThermiaGenesisClimate(CoordinatorEntity[ThermiaGenesisCoordinator], ClimateEntity):
    """A circuit the pump heats: on or off with a coil of the heat pump unit."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TARGET_STEP
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]  # noqa: RUF012
    # The coil, the set points and the measured temperature and running demands.
    _groups = (GROUPS["coil"], GROUPS["holding"], GROUPS["input"])

    entity_description: ThermiaGenesisClimateEntityDescription

    def __init__(self, coordinator: ThermiaGenesisCoordinator) -> None:
        """Show the circuit of the pump ``coordinator`` reads."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        part = self.entity_description.key
        self._attr_unique_id = f"{entry_id}_{part}_climate"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{part}")})
        validator = self.entity_description.set_point.validator
        if isinstance(validator, Between):
            self._attr_min_temp = validator.low
            self._attr_max_temp = validator.high

    @property
    def available(self) -> bool:
        """Unavailable while a register space it reads fails to refresh."""
        failed = self.coordinator.data.failed
        return super().available and not any(group in failed for group in self._groups)

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Heat while the circuit is enabled."""
        enabled = getattr(self.coordinator.pump.heat_pump, self.entity_description.enable.name)
        if enabled is None:
            return None
        return HVACMode.HEAT if enabled else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Heating while a demand that heats the circuit runs; off while it is disabled."""
        if self.hvac_mode is HVACMode.OFF:
            return HVACAction.OFF
        demands = self.coordinator.pump.status.running_demands
        if demands is None:
            return None
        return self._action(demands)

    def _action(self, demands: RunningDemands) -> HVACAction:
        return HVACAction.HEATING if demands & self.entity_description.heating else HVACAction.IDLE

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn the circuit on or off."""
        await self.coordinator.async_write(
            self.coordinator.pump.heat_pump,
            self.entity_description.enable,
            hvac_mode is HVACMode.HEAT,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Set the set points, and turn the circuit on or off first when asked to."""
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_handle_set_hvac_mode_service(hvac_mode)
        await self._async_set_set_points(kwargs)

    @abstractmethod
    async def _async_set_set_points(self, kwargs: dict[str, Any]) -> None:
        """Write the set points in ``kwargs``, the service data with °C values."""


class ThermiaGenesisHeating(ThermiaGenesisClimate):
    """The heating circuit: the room temperature, the comfort wheel and heating on or off."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    entity_description = ThermiaGenesisClimateEntityDescription(
        key="heat",
        enable=HeatPumpUnit.enable_heat,
        set_point=Heat.comfort_wheel_setting,
        heating=RunningDemands.HEAT,
    )

    @property
    def current_temperature(self) -> float | None:
        """The room temperature."""
        return self.coordinator.pump.heat_pump.room_temperature

    @property
    def target_temperature(self) -> float | None:
        """The comfort wheel setting."""
        return self.coordinator.pump.heat.comfort_wheel_setting

    def _action(self, demands: RunningDemands) -> HVACAction:
        if RunningDemands.DEFROST in demands:
            return HVACAction.DEFROSTING
        return super()._action(demands)

    async def _async_set_set_points(self, kwargs: dict[str, Any]) -> None:
        field = Heat.comfort_wheel_setting
        value = to_register(field, kwargs[ATTR_TEMPERATURE])
        await self.coordinator.async_write(self.coordinator.pump.heat, field, value)


class ThermiaGenesisHotWater(ThermiaGenesisClimate):
    """The hot water: its temperature, heated from the start to the stop temperature."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    entity_description = ThermiaGenesisClimateEntityDescription(
        key="tap_water",
        enable=HeatPumpUnit.enable_tap_water,
        set_point=TapWater.start_temperature,
        heating=RunningDemands.HOT_WATER | RunningDemands.ANTI_LEGIONELLA,
    )

    @property
    def current_temperature(self) -> float | None:
        """The weighted hot water temperature."""
        return self.coordinator.pump.tap_water.weighted_temperature

    @property
    def target_temperature_low(self) -> float | None:
        """The temperature the pump starts heating the water at."""
        return self.coordinator.pump.tap_water.start_temperature

    @property
    def target_temperature_high(self) -> float | None:
        """The temperature the pump stops heating the water at."""
        return self.coordinator.pump.tap_water.stop_temperature

    async def _async_set_set_points(self, kwargs: dict[str, Any]) -> None:
        """Write the start and stop so that the start stays below the stop after each."""
        start = to_register(TapWater.start_temperature, kwargs[ATTR_TARGET_TEMP_LOW])
        stop = to_register(TapWater.stop_temperature, kwargs[ATTR_TARGET_TEMP_HIGH])
        if start >= stop:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="start_not_below_stop",
                translation_placeholders={"start": str(start), "stop": str(stop)},
            )
        writes = [(TapWater.start_temperature, start), (TapWater.stop_temperature, stop)]
        # Raising the start to or above the current stop: write the stop first. A stop that
        # reads as unknown can't be written either, so the order doesn't matter then.
        if start >= (self.target_temperature_high or stop):
            writes.reverse()
        tap_water = self.coordinator.pump.tap_water
        for field, value in writes:
            await self.coordinator.async_write(tap_water, field, value)
