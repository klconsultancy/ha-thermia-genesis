"""Sensors: the numbers and enums of the pump."""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from thermia_genesis.v17_1.enums import Demand, OperationalMode

from .entity import ThermiaGenesisEntity, ThermiaGenesisEntityDescription

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import ThermiaGenesisConfigEntry

# Coordinator-based: the entities never update on their own.
PARALLEL_UPDATES = 0

# Home Assistant's unit for each unit the library declares.
UNITS: dict[str | None, str] = {}


@dataclass(frozen=True, kw_only=True)
class ThermiaGenesisSensorEntityDescription(
    ThermiaGenesisEntityDescription, SensorEntityDescription
):
    """A sensor for one field of a part."""


def _options(enum: type[Enum]) -> list[str]:
    return [member.name.lower() for member in enum]


def _demand(key: str, *, enabled: bool = False) -> ThermiaGenesisSensorEntityDescription:
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENUM,
        options=_options(Demand),
        entity_registry_enabled_default=enabled,
    )


# The sensors of each part, by the part's attribute on ThermiaGenesis.
SENSORS: dict[str, tuple[ThermiaGenesisSensorEntityDescription, ...]] = {
    "status": (
        ThermiaGenesisSensorEntityDescription(
            key="operational_mode",
            translation_key="operational_mode",
            device_class=SensorDeviceClass.ENUM,
            options=_options(OperationalMode),
        ),
        _demand("running_demand_1", enabled=True),
        _demand("running_demand_2"),
        _demand("running_demand_3"),
        _demand("queued_demand_1"),
        _demand("queued_demand_2"),
        _demand("queued_demand_3"),
        _demand("queued_demand_4"),
        _demand("queued_demand_5"),
    ),
}


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
