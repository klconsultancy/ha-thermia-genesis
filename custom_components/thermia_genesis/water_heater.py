"""Water heaters: the hot water, heated by the heat pump up to its stop temperature."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.water_heater import WaterHeaterEntity
from homeassistant.components.water_heater.const import (
    ATTR_OPERATION_MODE,
    STATE_HEAT_PUMP,
    WaterHeaterEntityFeature,
)
from homeassistant.const import ATTR_TEMPERATURE, STATE_OFF, UnitOfTemperature
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from thermia_genesis.subsystem import Between
from thermia_genesis.v17_1.heat_pump_unit import HeatPumpUnit
from thermia_genesis.v17_1.tap_water import TapWater

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator
from .entity import GROUPS, to_register

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ThermiaGenesisConfigEntry

# Coordinator-based, so no updates of its own; one write at a time.
PARALLEL_UPDATES = 1

# The fields the water heater stands for, by part; they have no sensor (docs/design.md).
FIELDS: dict[str, set[str]] = {
    "heat_pump": {"enable_tap_water"},
    "tap_water": {"stop_temperature"},
}

# The step the card offers; the register itself takes 0.01.
TARGET_STEP = 0.5


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the hot water."""
    async_add_entities([ThermiaGenesisHotWater(entry.runtime_data)])


class ThermiaGenesisHotWater(CoordinatorEntity[ThermiaGenesisCoordinator], WaterHeaterEntity):
    """The hot water: reheated below a number, "Reheat below", up to the stop temperature.

    The target is the stop temperature. It has no low and high target: they read as a range,
    but a water heater sets only its one target, so on 0.3.0-rc.1 changing the low value
    set the stop.
    """

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = TARGET_STEP
    _attr_operation_list = [STATE_OFF, STATE_HEAT_PUMP]  # noqa: RUF012
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.ON_OFF
    )
    # The enable coil, the start and stop, and the water temperature.
    _groups = (GROUPS["coil"], GROUPS["holding"], GROUPS["input"])

    def __init__(self, coordinator: ThermiaGenesisCoordinator) -> None:
        """Show the hot water of the pump ``coordinator`` reads."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_tap_water_water_heater"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_tap_water")})
        validator = TapWater.stop_temperature.validator
        if isinstance(validator, Between):
            self._attr_min_temp = validator.low
            self._attr_max_temp = validator.high

    @property
    def available(self) -> bool:
        """Unavailable while a register space it reads fails to refresh."""
        failed = self.coordinator.data.failed
        return super().available and not any(group in failed for group in self._groups)

    @property
    def current_operation(self) -> str | None:
        """Heat pump while hot water is enabled, off otherwise."""
        enabled = self.coordinator.pump.heat_pump.enable_tap_water
        if enabled is None:
            return None
        return STATE_HEAT_PUMP if enabled else STATE_OFF

    @property
    def current_temperature(self) -> float | None:
        """The temperature at the top of the tank, what the tap gives."""
        return self.coordinator.pump.tap_water.top_temperature

    @property
    def target_temperature(self) -> float | None:
        """The temperature the pump stops heating the water at."""
        return self.coordinator.pump.tap_water.stop_temperature

    async def async_set_temperature(self, **kwargs: Any) -> None:  # noqa: ANN401
        """Set the stop temperature, above the start; set the operation mode first if asked.

        The start is the one last written, since a write reads back only after the cooldown.
        """
        tap_water = self.coordinator.pump.tap_water
        stop = to_register(TapWater.stop_temperature, kwargs[ATTR_TEMPERATURE])

        def check() -> None:
            start = self.coordinator.latest(tap_water, TapWater.start_temperature)
            if start is not None and start >= stop:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="start_not_below_stop",
                    translation_placeholders={"start": str(start), "stop": str(stop)},
                )

        # Refuse a stop before changing the operation mode, so a refusal changes nothing.
        check()
        if (operation_mode := kwargs.get(ATTR_OPERATION_MODE)) is not None:
            await self.async_handle_set_operation_mode(operation_mode)
        await self.coordinator.async_write(tap_water, TapWater.stop_temperature, stop, check=check)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Turn hot water on (heat pump) or off."""
        await self.coordinator.async_write(
            self.coordinator.pump.heat_pump,
            HeatPumpUnit.enable_tap_water,
            operation_mode == STATE_HEAT_PUMP,
        )

    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Turn hot water on."""
        await self.async_set_operation_mode(STATE_HEAT_PUMP)

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: ANN401, ARG002
        """Turn hot water off."""
        await self.async_set_operation_mode(STATE_OFF)
