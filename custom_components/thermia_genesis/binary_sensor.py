"""Binary sensors: the coils, discrete inputs and flags of the pump."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import BinarySensorEntity

from .entity import ThermiaGenesisEntity
from .parts import heat_pump, status

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ThermiaGenesisConfigEntry
    from .descriptions import ThermiaGenesisBinarySensorEntityDescription

# Coordinator-based: the entities never update on their own.
PARALLEL_UPDATES = 0


# The binary sensors of each part, by the part's attribute on ThermiaGenesis.
BINARY_SENSORS: dict[str, tuple[ThermiaGenesisBinarySensorEntityDescription, ...]] = {
    "heat_pump": heat_pump.BINARY_SENSORS,
    "status": status.BINARY_SENSORS,
}


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a binary sensor for each bit of the parts the pump has."""
    coordinator = entry.runtime_data
    async_add_entities(
        ThermiaGenesisBinarySensor(coordinator, part, description)
        for part, descriptions in BINARY_SENSORS.items()
        if getattr(coordinator.pump, part) is not None
        for description in descriptions
    )


class ThermiaGenesisBinarySensor(ThermiaGenesisEntity, BinarySensorEntity):
    """A bit of the pump."""

    entity_description: ThermiaGenesisBinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """The bit, or whether the flags field holds the member."""
        value = self._value
        member = self.entity_description.member
        if value is None or member is None:
            return value  # type: ignore[no-any-return]
        return member in value
