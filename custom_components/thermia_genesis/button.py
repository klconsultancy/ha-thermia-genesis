"""Buttons: resetting the pump's alarms."""

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from thermia_genesis.v17_1.heat_pump_unit import HeatPumpUnit

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ThermiaGenesisConfigEntry

# Coordinator-based, so no updates of its own; one write at a time.
PARALLEL_UPDATES = 1

# The fields each button stands for, by part; they have no sensor (docs/design.md).
FIELDS: dict[str, set[str]] = {"heat_pump": {"reset_all_alarms"}}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the button that resets the alarms."""
    async_add_entities([ThermiaGenesisResetAlarms(entry.runtime_data)])


class ThermiaGenesisResetAlarms(CoordinatorEntity[ThermiaGenesisCoordinator], ButtonEntity):
    """Reset the pump's alarms, next to the aggregate alarm on the main device."""

    _attr_has_entity_name = True
    entity_description = ButtonEntityDescription(key="reset_alarms", translation_key="reset_alarms")

    def __init__(self, coordinator: ThermiaGenesisCoordinator) -> None:
        """Reset the alarms of the pump ``coordinator`` reads."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_reset_alarms"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    async def async_press(self) -> None:
        """Turn the pump's reset coil on; the pump turns it off itself (library errata)."""
        await self.coordinator.async_write(
            self.coordinator.pump.heat_pump,
            HeatPumpUnit.reset_all_alarms,
            True,  # noqa: FBT003
        )
