"""The base of every Thermia Genesis entity."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator

if TYPE_CHECKING:
    from thermia_genesis import ThermiaGenesis
    from thermia_genesis.subsystem import Field, Space, Subsystem

# The register space of a field, as the coordinator's UpdateReport names it.
GROUPS: dict[Space, str] = {
    "coil": "coils",
    "discrete": "discrete_inputs",
    "input": "input_registers",
    "holding": "holding_registers",
}

# Status belongs to the pump's own device rather than to a device of its own.
MAIN_DEVICE_PARTS = {"status"}


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisEntityDescription(EntityDescription):
    """An entity for one field of a part; ``key`` is the field unless ``field`` says otherwise."""

    field: str | None = None

    @property
    def field_name(self) -> str:
        """The name of the library field this entity shows."""
        return self.field or self.key


def to_register(field: Field[Any], value: float) -> float:
    """Round ``value`` to ``field``'s resolution, an int for a whole-number register.

    Home Assistant converts units (°F to °C) and passes numbers as floats without rounding,
    which the library refuses for a value finer than the register.
    """
    resolution = field.resolution or 1
    if resolution >= 1:
        return round(value / resolution) * int(resolution)
    return round(round(value / resolution) * resolution, 6)


def field_value(pump: ThermiaGenesis, part: str, field: str) -> Any:  # noqa: ANN401
    """Return the value of ``part``'s ``field``; its type depends on the field."""
    return getattr(getattr(pump, part), field)


class ThermiaGenesisEntity(CoordinatorEntity[ThermiaGenesisCoordinator]):
    """An entity showing one field of one part of the pump."""

    _attr_has_entity_name = True
    entity_description: ThermiaGenesisEntityDescription

    def __init__(
        self,
        coordinator: ThermiaGenesisCoordinator,
        part: str,
        description: ThermiaGenesisEntityDescription,
    ) -> None:
        """Show ``description``'s field of ``part``."""
        super().__init__(coordinator)
        self.entity_description = description
        self._part = part
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{part}_{description.key}"
        device = entry_id if part in MAIN_DEVICE_PARTS else f"{entry_id}_{part}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, device)})
        # The library's field, the class attribute: what it accepts and where it lives.
        self._field: Field[Any] = getattr(type(self._subsystem), description.field_name)
        self._group = GROUPS[self._field.space]

    @property
    def _subsystem(self) -> Subsystem:
        return getattr(self.coordinator.pump, self._part)  # type: ignore[no-any-return]

    @property
    def _value(self) -> Any:  # noqa: ANN401
        """The field's value; its type depends on the field."""
        return field_value(self.coordinator.pump, self._part, self.entity_description.field_name)

    @property
    def available(self) -> bool:
        """Unavailable while the field's register space fails to refresh."""
        return super().available and self._group not in self.coordinator.data.failed
