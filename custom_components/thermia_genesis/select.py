"""Selects: the writable enum settings of the pump."""

from typing import TYPE_CHECKING, cast

from homeassistant.components.select import SelectEntity

from .entity import ThermiaGenesisEntity
from .parts import SELECTS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from thermia_genesis.subsystem import MemberOf

    from .coordinator import ThermiaGenesisConfigEntry, ThermiaGenesisCoordinator
    from .descriptions import ThermiaGenesisSelectEntityDescription

# Coordinator-based, so no updates of its own; one write at a time.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a select for each writable enum field of the parts the pump has."""
    coordinator = entry.runtime_data
    async_add_entities(
        ThermiaGenesisSelect(coordinator, part, description)
        for part, descriptions in SELECTS.items()
        if getattr(coordinator.pump, part) is not None
        for description in descriptions
    )


class ThermiaGenesisSelect(ThermiaGenesisEntity, SelectEntity):
    """A writable enum of the pump; an option is a member's lowercase name."""

    entity_description: ThermiaGenesisSelectEntityDescription

    def __init__(
        self,
        coordinator: ThermiaGenesisCoordinator,
        part: str,
        description: ThermiaGenesisSelectEntityDescription,
    ) -> None:
        """Offer the members ``description``'s field accepts."""
        super().__init__(coordinator, part, description)
        # A test holds every select's field to a MemberOf validator.
        self._enum = cast("MemberOf", self._field.validator).enum
        self._attr_options = [member.name.lower() for member in self._enum]

    @property
    def current_option(self) -> str | None:
        """The member the pump reports; unknown for a value the library doesn't know."""
        value = self._value
        return None if value is None else value.name.lower()

    async def async_select_option(self, option: str) -> None:
        """Write the member named ``option``."""
        await self.coordinator.async_write(self._subsystem, self._field, self._enum[option.upper()])
