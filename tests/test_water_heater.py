"""The hot water: a water heater heating to the stop temperature, and its start temperature."""

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Literal
from unittest.mock import patch

import pytest
from homeassistant.components.number.const import ATTR_VALUE, SERVICE_SET_VALUE
from homeassistant.components.number.const import DOMAIN as NUMBER_DOMAIN
from homeassistant.components.water_heater.const import (
    ATTR_OPERATION_MODE,
    SERVICE_SET_OPERATION_MODE,
    SERVICE_SET_TEMPERATURE,
    STATE_HEAT_PUMP,
)
from homeassistant.components.water_heater.const import DOMAIN as WATER_HEATER_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_HOST,
    CONF_PORT,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from modbus_connection.exceptions import IllegalDataAddressError, ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit
    from modbus_connection.model import UpdateReport

HOT_WATER = "water_heater.hot_water"
START = "number.hot_water_reheat_below"


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


def state(hass: HomeAssistant, entity_id: str) -> State:
    found = hass.states.get(entity_id)
    assert found is not None, entity_id
    return found


async def set_stop(hass: HomeAssistant, temperature: float, **data: object) -> None:
    await hass.services.async_call(
        WATER_HEATER_DOMAIN,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: HOT_WATER, ATTR_TEMPERATURE: temperature, **data},
        blocking=True,
    )


async def set_start(hass: HomeAssistant, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: START, ATTR_VALUE: value},
        blocking=True,
    )


async def test_heats_the_water_to_the_stop_temperature(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    heater = state(hass, HOT_WATER)
    assert heater.state == STATE_HEAT_PUMP
    # The top temperature, what the tap gives: 49.35, shown in tenths.
    assert heater.attributes["current_temperature"] == 49.4
    assert heater.attributes[ATTR_TEMPERATURE] == 55.0
    # One target only: with a low and a high, the card draws a range whose low handle
    # sets the target, so moving the start would move the stop (docs/design.md).
    assert heater.attributes["target_temp_low"] is None
    assert heater.attributes["target_temp_high"] is None
    assert (heater.attributes["min_temp"], heater.attributes["max_temp"]) == (35, 60)
    assert heater.attributes["target_temp_step"] == 0.5


async def test_offers_the_start_temperature(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await setup(hass, entry)

    start = state(hass, START)
    assert start.state == "45.0"
    assert (start.attributes["min"], start.attributes["max"]) == (35, 60)
    assert start.attributes["step"] == 0.5
    assert start.attributes["unit_of_measurement"] == UnitOfTemperature.CELSIUS


async def test_is_off_while_hot_water_is_disabled(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[8] = False

    await setup(hass, entry)

    assert state(hass, HOT_WATER).state == STATE_OFF


async def test_sets_the_stop_temperature(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await set_stop(hass, 52.5)

    assert pump_unit.holding[23] == 5250
    assert state(hass, HOT_WATER).attributes[ATTR_TEMPERATURE] == 52.5


async def test_sets_the_start_temperature(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await set_start(hass, 47.5)

    assert pump_unit.holding[22] == 4750
    assert state(hass, START).state == "47.5"


@pytest.mark.parametrize("stop", [45.0, 40.0])
async def test_refuses_a_stop_not_above_the_start(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit, stop: float
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError) as raised:
        await set_stop(hass, stop)

    assert raised.value.translation_key == "start_not_below_stop"
    assert pump_unit.holding[23] == 5500


@pytest.mark.parametrize("start", [55.0, 58.0])
async def test_refuses_a_start_not_below_the_stop(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit, start: float
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError) as raised:
        await set_start(hass, start)

    assert raised.value.translation_key == "start_not_below_stop"
    assert pump_unit.holding[22] == 4500


async def test_checks_the_start_against_a_stop_just_written(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    # The read-back of the stop waits for the cooldown after the first write.
    await set_start(hass, 40.0)
    await set_stop(hass, 44.0)
    with pytest.raises(ServiceValidationError):
        await set_start(hass, 50.0)

    assert (pump_unit.holding[22], pump_unit.holding[23]) == (4000, 4400)


async def test_refuses_a_stop_out_of_range(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await set_stop(hass, 65.0)

    assert pump_unit.holding[23] == 5500


async def test_rounds_the_stop_to_the_register(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    await setup(hass, entry)

    # 130 °F is 54.444... °C.
    await set_stop(hass, 130)

    assert pump_unit.holding[23] == 5444


@pytest.mark.parametrize(
    ("service", "data", "coil"),
    [
        (SERVICE_TURN_OFF, {}, False),
        (SERVICE_SET_OPERATION_MODE, {ATTR_OPERATION_MODE: STATE_OFF}, False),
        (SERVICE_TURN_ON, {}, True),
        (SERVICE_SET_OPERATION_MODE, {ATTR_OPERATION_MODE: STATE_HEAT_PUMP}, True),
    ],
)
async def test_turns_hot_water_off_and_on(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    service: str,
    data: dict[str, object],
    coil: bool,  # noqa: FBT001
) -> None:
    pump_unit.coil[8] = not coil
    await setup(hass, entry)

    await hass.services.async_call(
        WATER_HEATER_DOMAIN, service, {ATTR_ENTITY_ID: HOT_WATER, **data}, blocking=True
    )

    assert pump_unit.coil[8] is coil


async def test_refuses_an_operation_mode_it_lacks(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await set_stop(hass, 52.0, **{ATTR_OPERATION_MODE: "gas"})

    assert pump_unit.coil[8] is True
    assert pump_unit.holding[23] == 5500


async def test_sets_the_mode_and_the_stop_at_once(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[8] = False
    await setup(hass, entry)

    await set_stop(hass, 52.0, **{ATTR_OPERATION_MODE: STATE_HEAT_PUMP})

    assert pump_unit.coil[8] is True
    assert pump_unit.holding[23] == 5200


async def test_reads_unknown_while_hot_water_is_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_read(8, IllegalDataAddressError(), register_type="coil")

    await setup(hass, entry)

    assert state(hass, HOT_WATER).state == STATE_UNKNOWN


async def test_sets_the_stop_while_the_start_is_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_read(22, IllegalDataAddressError(), register_type="holding")
    await setup(hass, entry)

    await set_stop(hass, 50.0)

    assert pump_unit.holding[23] == 5000


@pytest.mark.parametrize(("space", "address"), [("holding", 23), ("input", 15), ("coil", 8)])
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

    assert state(hass, HOT_WATER).state == STATE_UNAVAILABLE


async def test_an_entry_from_before_drops_the_sensors_they_replace(
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
        ("sensor", f"{entry.entry_id}_tap_water_start_temperature"),
        ("sensor", f"{entry.entry_id}_tap_water_stop_temperature"),
        ("binary_sensor", f"{entry.entry_id}_heat_pump_enable_tap_water"),
    ]
    for platform, unique_id in replaced:
        entity_registry.async_get_or_create(platform, DOMAIN, unique_id, config_entry=entry)

    await setup(hass, entry)

    for platform, unique_id in replaced:
        assert entity_registry.async_get_entity_id(platform, DOMAIN, unique_id) is None


async def test_a_write_waits_for_a_poll_in_flight(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)
    coordinator = entry.runtime_data
    read, resume = asyncio.Event(), asyncio.Event()
    update = coordinator.pump.async_update

    async def paused_update() -> UpdateReport:
        report: UpdateReport = await update()  # reads the stop as 55 here
        read.set()
        await resume.wait()
        return report

    with patch.object(coordinator.pump, "async_update", paused_update):
        poll = hass.async_create_task(coordinator.async_refresh())
        await read.wait()
        # The stop is lowered while the poll is in flight: the write waits for it.
        lower = hass.async_create_task(set_stop(hass, 48.0))
        await asyncio.sleep(0)
        assert pump_unit.holding[23] == 5500
        resume.set()
        await poll
        await lower

    # Within the cooldown, the start is checked against the stop just written.
    with pytest.raises(ServiceValidationError):
        await set_start(hass, 50.0)
    assert (pump_unit.holding[22], pump_unit.holding[23]) == (4500, 4800)


async def test_a_refused_stop_leaves_the_operation_mode(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await set_stop(hass, 45.0, **{ATTR_OPERATION_MODE: STATE_OFF})

    assert pump_unit.coil[8] is True
