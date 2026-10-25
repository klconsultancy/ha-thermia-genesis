"""The base of every Thermia Genesis entity."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator

if TYPE_CHECKING:
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
        library_field: Field[Any] = getattr(type(self._subsystem), description.field_name)
        self._group = GROUPS[library_field.space]

    @property
    def _subsystem(self) -> Subsystem:
        return getattr(self.coordinator.pump, self._part)  # type: ignore[no-any-return]

    @property
    def _value(self) -> Any:  # noqa: ANN401
        """The field's value; its type depends on the field."""
        return getattr(self._subsystem, self.entity_description.field_name)

    @property
    def available(self) -> bool:
        """Unavailable while the field's register space fails to refresh."""
        return super().available and self._group not in self.coordinator.data.failed
