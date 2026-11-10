"""Numbers: the writable numeric settings, such as power consumption control."""

from datetime import timedelta
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components.number.const import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    SERVICE_SET_VALUE,
)
from homeassistant.components.number.const import DOMAIN as NUMBER_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_HOST,
    CONF_PORT,
    STATE_UNAVAILABLE,
    EntityCategory,
    UnitOfPower,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from modbus_connection.exceptions import ServerDeviceBusyError, ServerDeviceFailureError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from thermia_genesis.v17_1.heat import Heat
from thermia_genesis.v17_1.heat_pump_unit import HeatPumpUnit

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN
from custom_components.thermia_genesis.entity import to_register

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit
    from thermia_genesis.subsystem import Field

MODE = "number.heat_pump_unit_power_consumption_control_mode"
LIMIT = "number.heat_pump_unit_input_power_limit"


@pytest.fixture
def entry(hass: HomeAssistant, unit: object) -> MockConfigEntry:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    return entry


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def number(hass: HomeAssistant, entity_id: str) -> State:
    found = hass.states.get(entity_id)
    assert found is not None, entity_id
    return found


async def set_value(hass: HomeAssistant, entity_id: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity_id, ATTR_VALUE: value},
        blocking=True,
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_offers_the_range_and_step_the_library_accepts(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    mode = number(hass, MODE)
    assert mode.state == "0"
    assert (mode.attributes[ATTR_MIN], mode.attributes[ATTR_MAX]) == (0, 3)
    assert mode.attributes[ATTR_STEP] == 1
    limit = number(hass, LIMIT)
    assert limit.state == "0.0"
    assert (limit.attributes[ATTR_MIN], limit.attributes[ATTR_MAX]) == (0, 3276.7)
    assert limit.attributes[ATTR_STEP] == 0.1
    assert limit.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfPower.KILO_WATT


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sets_the_power_limit(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await set_value(hass, LIMIT, 2.5)

    assert pump_unit.holding[125] == 25
    assert number(hass, LIMIT).state == "2.5"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_sets_the_control_mode_as_an_integer(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    # Home Assistant passes a float.
    await set_value(hass, MODE, 1)

    assert pump_unit.holding[124] == 1


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_refuses_a_value_out_of_range(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await set_value(hass, MODE, 4)

    assert pump_unit.holding[124] == 0


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_rounds_a_value_to_the_register(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await set_value(hass, LIMIT, 2.54)

    assert pump_unit.holding[125] == 25


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_reports_a_pump_that_fails_the_write(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)
    pump_unit.fail_write(125, ServerDeviceFailureError(5))

    with pytest.raises(HomeAssistantError) as raised:
        await set_value(hass, LIMIT, 2.0)

    assert raised.value.translation_key == "write_failed"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_is_unavailable_while_the_holding_registers_fail(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(124, ServerDeviceBusyError(), register_type="holding")

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert number(hass, MODE).state == STATE_UNAVAILABLE


async def test_is_disabled_by_default_among_the_settings(
    hass: HomeAssistant, entry: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    await setup(hass, entry)

    for entity_id in (MODE, LIMIT):
        entity = entity_registry.async_get(entity_id)
        assert entity is not None, entity_id
        assert entity.disabled
        assert entity.entity_category is EntityCategory.CONFIG


async def test_an_entry_from_before_the_numbers_drops_the_sensors_they_replace(
    hass: HomeAssistant, unit: object, entity_registry: er.EntityRegistry
) -> None:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1},
        minor_version=1,
    )
    entry.add_to_hass(hass)
    replaced = [
        f"{entry.entry_id}_heat_pump_power_consumption_control_mode",
        f"{entry.entry_id}_heat_pump_input_power_limit",
    ]
    for unique_id in replaced:
        entity_registry.async_get_or_create("sensor", DOMAIN, unique_id, config_entry=entry)

    await setup(hass, entry)

    for unique_id in replaced:
        assert entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id) is None


@pytest.mark.parametrize(
    ("field", "value", "written"),
    [
        (HeatPumpUnit.power_consumption_control_mode, 1.0, 1),
        (HeatPumpUnit.input_power_limit, 2.549, 2.5),
        (Heat.comfort_wheel_setting, 21.111111, 21.11),
    ],
)
def test_a_value_is_rounded_to_its_register(
    field: Field[Any], value: float, written: float
) -> None:
    rounded = to_register(field, value)

    assert rounded == written
    # An integer register gets an int, not a float that happens to be whole.
    assert type(rounded) is type(written)
