"""Numbers: the writable numeric settings of the pump."""

from typing import TYPE_CHECKING, cast

from homeassistant.components.number import NumberEntity

from .entity import ThermiaGenesisEntity, to_register
from .parts import NUMBERS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from thermia_genesis.subsystem import Between

    from .coordinator import ThermiaGenesisConfigEntry, ThermiaGenesisCoordinator
    from .descriptions import ThermiaGenesisNumberEntityDescription

# Coordinator-based, so no updates of its own; one write at a time.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a number for each writable numeric field of the parts the pump has."""
    coordinator = entry.runtime_data
    async_add_entities(
        ThermiaGenesisNumber(coordinator, part, description)
        for part, descriptions in NUMBERS.items()
        if getattr(coordinator.pump, part) is not None
        for description in descriptions
    )


class ThermiaGenesisNumber(ThermiaGenesisEntity, NumberEntity):
    """A writable number of the pump, within the range and step the library accepts."""

    entity_description: ThermiaGenesisNumberEntityDescription

    def __init__(
        self,
        coordinator: ThermiaGenesisCoordinator,
        part: str,
        description: ThermiaGenesisNumberEntityDescription,
    ) -> None:
        """Offer the range and step of ``description``'s field."""
        super().__init__(coordinator, part, description)
        # A test holds every number's field to a Between validator.
        validator = cast("Between", self._field.validator)
        self._attr_native_min_value = validator.low
        self._attr_native_max_value = validator.high
        # A register always has a resolution; only a bit has none.
        self._attr_native_step = self._field.resolution or 1

    @property
    def native_value(self) -> float | None:
        """The value the pump reports."""
        return self._value  # type: ignore[no-any-return]

    async def async_set_native_value(self, value: float) -> None:
        """Write ``value``, rounded to the register's resolution."""
        await self.coordinator.async_write(
            self._subsystem, self._field, to_register(self._field, value)
        )
