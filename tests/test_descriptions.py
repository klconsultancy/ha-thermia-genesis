"""The entity descriptions cover the library's fields, as docs/design.md (Entities) requires."""

import asyncio
import json
from enum import IntEnum, IntFlag
from pathlib import Path

import pytest
from homeassistant.components.sensor import SensorDeviceClass
from modbus_connection.mock import MockModbusConnection
from thermia_genesis import ThermiaGenesis
from thermia_genesis.subsystem import Field, Subsystem

from custom_components.thermia_genesis.binary_sensor import BINARY_SENSORS
from custom_components.thermia_genesis.const import PARTS
from custom_components.thermia_genesis.descriptions import UNITS
from custom_components.thermia_genesis.sensor import SENSORS

# The parts whose every field has an entity; it grows with each part's pull request.
COMPLETE = ["heat_pump", "status"]


async def _read_every_part() -> dict[str, type[Subsystem]]:
    """The library's class of each part, from a pump that has every optional part."""
    unit = MockModbusConnection().for_unit(1)
    # Every coil on, so every "Enable ..." coil is, whichever the library reads.
    for address in range(10000):
        unit.coil[address] = True
    pump = ThermiaGenesis(unit)
    await pump.async_update()
    return {name: type(value) for name, value in vars(pump).items() if isinstance(value, Subsystem)}


CLASSES = asyncio.run(_read_every_part())

STRINGS = json.loads(
    (
        Path(__file__).parent.parent / "custom_components" / "thermia_genesis" / "strings.json"
    ).read_text(encoding="utf-8")
)


def fields(part: str) -> dict[str, Field[object]]:
    """The library's fields of ``part``, by name."""
    subsystem = CLASSES[part]
    return {
        name: value
        for klass in reversed(subsystem.__mro__)
        for name, value in vars(klass).items()
        if isinstance(value, Field)
    }


def convert(field: Field[object]) -> type | None:
    return getattr(field.field, "convert", None)


def described(part: str) -> list[str]:
    """The field (or field and flag member) each description of ``part`` stands for."""
    names = [d.field or d.key for d in SENSORS.get(part, ())]
    for description in BINARY_SENSORS.get(part, ()):
        name = description.field or description.key
        member = description.member
        names.append(name if member is None else f"{name}.{member.name}")
    return names


def expected(part: str) -> list[str]:
    names: list[str] = []
    for name, field in fields(part).items():
        kind = convert(field)
        if isinstance(kind, type) and issubclass(kind, IntFlag):
            names.extend(f"{name}.{member.name}" for member in kind)
        else:
            names.append(name)
    return names


def test_parts_are_the_library_parts() -> None:
    assert set(CLASSES) == {*PARTS, "status"}
    assert set(SENSORS) | set(BINARY_SENSORS) <= set(CLASSES)


@pytest.mark.parametrize("part", COMPLETE)
def test_every_field_of_a_complete_part_has_one_entity(part: str) -> None:
    assert sorted(described(part)) == sorted(expected(part))


@pytest.mark.parametrize("part", sorted({*SENSORS, *BINARY_SENSORS}))
def test_descriptions_stand_for_library_fields(part: str) -> None:
    assert set(described(part)) <= set(expected(part))
    assert len(described(part)) == len(set(described(part)))


@pytest.mark.parametrize("part", sorted(SENSORS))
def test_sensor_units_match_the_library(part: str) -> None:
    library = fields(part)
    for description in SENSORS[part]:
        unit = library[description.field or description.key].field.unit  # type: ignore[union-attr]
        assert unit is None or unit in UNITS, unit
        assert description.native_unit_of_measurement == UNITS.get(unit), description.key


@pytest.mark.parametrize("part", sorted(SENSORS))
def test_enum_sensors_offer_the_library_members(part: str) -> None:
    library = fields(part)
    for description in SENSORS[part]:
        kind = convert(library[description.field or description.key])
        if isinstance(kind, type) and issubclass(kind, IntEnum):
            assert description.device_class is SensorDeviceClass.ENUM, description.key
            assert description.options == [member.name.lower() for member in kind]
        else:
            assert description.device_class is not SensorDeviceClass.ENUM, description.key


@pytest.mark.parametrize("part", sorted(BINARY_SENSORS))
def test_binary_sensors_are_bits(part: str) -> None:
    library = fields(part)
    for description in BINARY_SENSORS[part]:
        field = library[description.field or description.key]
        if description.member is None:
            assert field.space in {"coil", "discrete"}, description.key
        else:
            assert isinstance(description.member, convert(field)), description.key  # type: ignore[arg-type]


def test_a_shared_translation_key_means_the_same_kind_of_sensor() -> None:
    kinds: dict[str | None, tuple[object, ...]] = {}
    for descriptions in SENSORS.values():
        for description in descriptions:
            kind = (
                description.device_class,
                description.options,
                description.native_unit_of_measurement,
            )
            assert kinds.setdefault(description.translation_key, kind) == kind, description.key


@pytest.mark.parametrize("part", sorted(SENSORS))
def test_every_enum_option_has_a_translation(part: str) -> None:
    sensors = STRINGS["entity"]["sensor"]
    for description in SENSORS[part]:
        if description.options is not None:
            states = sensors[description.translation_key]["state"]
            assert set(description.options) <= set(states), description.key
