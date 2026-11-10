"""The heating climate: room temperature, comfort wheel and heating on or off."""

from datetime import timedelta
from typing import TYPE_CHECKING, Literal
from unittest.mock import PropertyMock, patch

import pytest
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_PORT,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import ServiceValidationError
from modbus_connection.exceptions import IllegalDataAddressError, ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from thermia_genesis.subsystem import Field

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit

HEATING = "climate.heating"

# Running demands (input 2) with the heat demand's bit, and with none but "no demand".
HEATING_NOW = 1 << 3
NO_DEMAND = 1 << 10


@pytest.fixture
def entry(hass: HomeAssistant, unit: MagicMock) -> MockConfigEntry:
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


def climate(hass: HomeAssistant) -> State:
    found = hass.states.get(HEATING)
    assert found is not None
    return found


async def test_shows_the_room_and_the_comfort_wheel(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    state = climate(hass)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 22.8
    assert state.attributes[ATTR_TEMPERATURE] == 22.0
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_offers_the_range_the_library_accepts(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    state = climate(hass)
    assert state.attributes[ATTR_MIN_TEMP] == 10
    assert state.attributes[ATTR_MAX_TEMP] == 40
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 0.5


async def test_keeps_home_assistants_range_without_a_library_range(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    with patch.object(Field, "validator", new_callable=PropertyMock, return_value=None):
        await setup(hass, entry)

    state = climate(hass)
    assert state.attributes[ATTR_MIN_TEMP] == DEFAULT_MIN_TEMP
    assert state.attributes[ATTR_MAX_TEMP] == DEFAULT_MAX_TEMP


async def test_heats_while_a_heat_demand_runs(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.input[2] = HEATING_NOW

    await setup(hass, entry)

    assert climate(hass).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING


async def test_is_off_while_heating_is_disabled(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[9] = False
    pump_unit.input[2] = HEATING_NOW

    await setup(hass, entry)

    state = climate(hass)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.OFF


async def test_sets_the_comfort_wheel(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: HEATING, ATTR_TEMPERATURE: 21.5},
        blocking=True,
    )

    assert pump_unit.holding[5] == 2150
    assert climate(hass).attributes[ATTR_TEMPERATURE] == 21.5


async def test_refuses_a_temperature_out_of_range(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: HEATING, ATTR_TEMPERATURE: 45},
            blocking=True,
        )

    assert pump_unit.holding[5] == 2200


async def test_turns_heating_off_and_on(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: HEATING, ATTR_HVAC_MODE: HVACMode.OFF},
        blocking=True,
    )
    assert pump_unit.coil[9] is False
    assert climate(hass).state == HVACMode.OFF

    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: HEATING}, blocking=True
    )
    assert pump_unit.coil[9] is True

    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: HEATING}, blocking=True
    )
    assert pump_unit.coil[9] is False


async def test_sets_the_mode_and_the_temperature_at_once(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[9] = False
    await setup(hass, entry)

    await hass.services.async_call(
        CLIMATE_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: HEATING, ATTR_TEMPERATURE: 21.0, ATTR_HVAC_MODE: HVACMode.HEAT},
        blocking=True,
    )

    assert pump_unit.coil[9] is True
    assert pump_unit.holding[5] == 2100


async def test_reads_unknown_while_a_value_is_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_read(2, IllegalDataAddressError(), register_type="input")
    pump_unit.fail_read(9, IllegalDataAddressError(), register_type="coil")
    pump_unit.input[121] = 2000  # no room sensor

    await setup(hass, entry)

    state = climate(hass)
    assert state.state == STATE_UNKNOWN
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] is None
    # Home Assistant leaves an unknown action out.
    assert ATTR_HVAC_ACTION not in state.attributes


@pytest.mark.parametrize(("space", "address"), [("holding", 5), ("input", 121), ("coil", 9)])
async def test_is_unavailable_while_a_register_space_it_reads_fails(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
    space: Literal["holding", "input", "coil"],
    address: int,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(address, ServerDeviceBusyError(), register_type=space)

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert climate(hass).state == STATE_UNAVAILABLE


async def test_replaces_the_sensors_of_the_fields_it_sets(
    hass: HomeAssistant, entry: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    replaced = [
        ("sensor", f"{entry.entry_id}_heat_comfort_wheel_setting"),
        ("binary_sensor", f"{entry.entry_id}_heat_pump_enable_heat"),
    ]
    for platform, unique_id in replaced:
        entity_registry.async_get_or_create(platform, DOMAIN, unique_id, config_entry=entry)
    kept = entity_registry.async_get_or_create(
        "sensor", DOMAIN, f"{entry.entry_id}_heat_pump_room_temperature", config_entry=entry
    )

    await setup(hass, entry)

    for platform, unique_id in replaced:
        assert entity_registry.async_get_entity_id(platform, DOMAIN, unique_id) is None
    assert entity_registry.async_get(kept.entity_id) is not None
