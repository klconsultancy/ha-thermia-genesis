"""Climates: the house, heated by the pump and set with the comfort wheel."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    ATTR_HVAC_MODE,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from thermia_genesis.subsystem import Between
from thermia_genesis.v17_1.enums import RunningDemands
from thermia_genesis.v17_1.heat import Heat
from thermia_genesis.v17_1.heat_pump_unit import HeatPumpUnit

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator
from .entity import GROUPS, to_register

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ThermiaGenesisConfigEntry

# Coordinator-based, so no updates of its own; one write at a time.
PARALLEL_UPDATES = 1

# The fields each climate stands for, by part; they have no sensor (docs/design.md).
FIELDS: dict[str, set[str]] = {
    "heat": {"comfort_wheel_setting"},
    "heat_pump": {"enable_heat"},
}

# The step the card offers; the register itself takes 0.01.
TARGET_STEP = 0.5


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the house's climate."""
    async_add_entities([ThermiaGenesisHeating(entry.runtime_data)])


class ThermiaGenesisHeating(CoordinatorEntity[ThermiaGenesisCoordinator], ClimateEntity):
    """The house: the room temperature, the comfort wheel and heating on or off."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TARGET_STEP
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]  # noqa: RUF012
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    # The coil, the comfort wheel and the room temperature and running demands.
    _groups = (GROUPS["coil"], GROUPS["holding"], GROUPS["input"])

    def __init__(self, coordinator: ThermiaGenesisCoordinator) -> None:
        """Show the heating of the pump ``coordinator`` reads."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        # The pump's own device and a neutral id: the climate is the house's, so cooling
        # can join it as an HVAC mode (docs/design.md).
        self._attr_unique_id = f"{entry_id}_climate"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})
        validator = Heat.comfort_wheel_setting.validator
        if isinstance(validator, Between):
            self._attr_min_temp = validator.low
            self._attr_max_temp = validator.high

    @property
    def available(self) -> bool:
        """Unavailable while a register space it reads fails to refresh."""
        failed = self.coordinator.data.failed
        return super().available and not any(group in failed for group in self._groups)

    @property
    def current_temperature(self) -> float | None:
        """The room temperature."""
        return self.coordinator.pump.heat_pump.room_temperature

    @property
    def target_temperature(self) -> float | None:
        """The comfort wheel setting."""
        return self.coordinator.pump.heat.comfort_wheel_setting

    @property
    def hvac_mode(self) -> HVACMode | None:
        """Heat while heating is enabled."""
        enabled = self.coordinator.pump.heat_pump.enable_heat
        if enabled is None:
            return None
        return HVACMode.HEAT if enabled else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        """Defrosting or heating while that demand runs; off while heating is disabled."""
        if self.hvac_mode is HVACMode.OFF:
            return HVACAction.OFF
        demands = self.coordinator.pump.status.running_demands
        if demands is None:
            return None
        if RunningDemands.DEFROST in demands:
            return HVACAction.DEFROSTING
        return HVACAction.HEATING if RunningDemands.HEAT in demands else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Set the comfort wheel, and turn heating on or off first when asked to.

        The temperature is rounded to the register's resolution: Home Assistant converts
        °F to °C without rounding.
        """
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_handle_set_hvac_mode_service(hvac_mode)
        field = Heat.comfort_wheel_setting
        value = to_register(field, kwargs[ATTR_TEMPERATURE])
        await self.coordinator.async_write(self.coordinator.pump.heat, field, value)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Turn heating on or off."""
        await self.coordinator.async_write(
            self.coordinator.pump.heat_pump, HeatPumpUnit.enable_heat, hvac_mode is HVACMode.HEAT
        )
