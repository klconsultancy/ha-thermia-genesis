"""Binary sensors: the coils, discrete inputs and flags of the pump."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from thermia_genesis.v17_1.enums import RunningDemands

from .entity import ThermiaGenesisEntity, ThermiaGenesisEntityDescription

if TYPE_CHECKING:
    from enum import IntFlag

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ThermiaGenesisConfigEntry

# Coordinator-based: the entities never update on their own.
PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisBinarySensorEntityDescription(
    ThermiaGenesisEntityDescription, BinarySensorEntityDescription
):
    """A binary sensor for a bit of a part, or for one member of a flags field."""

    member: IntFlag | None = None


def _members(
    field: str, flags: type[IntFlag]
) -> tuple[ThermiaGenesisBinarySensorEntityDescription, ...]:
    """One binary sensor per member of a flags field, disabled by default."""
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


# The binary sensors of each part, by the part's attribute on ThermiaGenesis.
BINARY_SENSORS: dict[str, tuple[ThermiaGenesisBinarySensorEntityDescription, ...]] = {
    "status": _members("running_demands", RunningDemands),
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
