"""Sensors: the numbers and enums of the pump."""

from enum import Enum
from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity

from .entity import ThermiaGenesisEntity
from .parts import SENSORS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import ThermiaGenesisConfigEntry
    from .descriptions import ThermiaGenesisSensorEntityDescription

# Coordinator-based: the entities never update on their own.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a sensor for each numeric or enum field of the parts the pump has."""
    coordinator = entry.runtime_data
    async_add_entities(
        ThermiaGenesisSensor(coordinator, part, description)
        for part, descriptions in SENSORS.items()
        if getattr(coordinator.pump, part) is not None
        for description in descriptions
    )


class ThermiaGenesisSensor(ThermiaGenesisEntity, SensorEntity):
    """A number or an enum of the pump."""

    entity_description: ThermiaGenesisSensorEntityDescription

    @property
    def native_value(self) -> StateType:
        """The field's value; an enum as its lowercase member name."""
        value = self._value
        if isinstance(value, Enum):
            return value.name.lower()
        return value  # type: ignore[no-any-return]
