"""Binary sensors: the coils, discrete inputs and flags of the pump."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ThermiaGenesisCoordinator
from .entity import GROUPS, ThermiaGenesisEntity, field_value
from .parts import BINARY_SENSORS

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from .coordinator import ThermiaGenesisConfigEntry
    from .descriptions import ThermiaGenesisBinarySensorEntityDescription

# Coordinator-based: the entities never update on their own.
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add a binary sensor for each bit of the parts the pump has, and the aggregate alarm."""
    coordinator = entry.runtime_data
    present = [
        (part, description)
        for part, descriptions in BINARY_SENSORS.items()
        if getattr(coordinator.pump, part) is not None
        for description in descriptions
    ]
    alarms = [
        (part, description.field_name)
        for part, description in present
        if description.device_class is BinarySensorDeviceClass.PROBLEM
    ]
    async_add_entities(
        [
            *(ThermiaGenesisBinarySensor(coordinator, *pair) for pair in present),
            ThermiaGenesisAlarm(coordinator, alarms),
        ]
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


class ThermiaGenesisAlarm(CoordinatorEntity[ThermiaGenesisCoordinator], BinarySensorEntity):
    """On while any alarm input of the parts the pump has is on; the one to notify on."""

    _attr_has_entity_name = True
    entity_description = BinarySensorEntityDescription(
        key="alarm", translation_key="alarm", device_class=BinarySensorDeviceClass.PROBLEM
    )

    def __init__(
        self, coordinator: ThermiaGenesisCoordinator, alarms: list[tuple[str, str]]
    ) -> None:
        """Combine ``alarms``, the alarm inputs as (part, field) pairs.

        It reads the fields itself rather than the alarm sensors, which are disabled by
        default and so never added to Home Assistant.
        """
        super().__init__(coordinator)
        self._alarms = alarms
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_alarm"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry_id)})

    @property
    def available(self) -> bool:
        """Unavailable while the discrete inputs, where every alarm lives, fail to refresh."""
        return super().available and GROUPS["discrete"] not in self.coordinator.data.failed

    @property
    def is_on(self) -> bool | None:
        """Whether any alarm input is on; unknown while none is on and none is known."""
        values = [field_value(self.coordinator.pump, *alarm) for alarm in self._alarms]
        if any(values):
            return True
        if all(value is None for value in values):
            return None
        return False
