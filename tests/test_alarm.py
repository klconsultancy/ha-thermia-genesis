"""The aggregate alarm: one binary sensor on the pump that is on when any alarm input is."""

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.components.binary_sensor.const import BinarySensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    CONF_HOST,
    CONF_PORT,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from modbus_connection.exceptions import ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit

ALARM = "binary_sensor.thermia_genesis_alarm"


@pytest.fixture
def entry(hass: HomeAssistant, unit: MagicMock) -> MockConfigEntry:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "10.64.30.14", CONF_PORT: 502, CONF_UNIT_ID: 1},
        entry_id="01JTHERMIAGENESIS000000000",
    )
    entry.add_to_hass(hass)
    return entry


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def refresh(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_is_off_on_the_main_device_and_enabled(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    await setup(hass, entry)

    state = hass.states.get(ALARM)
    assert state is not None
    assert state.state == STATE_OFF
    assert state.attributes[ATTR_DEVICE_CLASS] == BinarySensorDeviceClass.PROBLEM
    registered = entity_registry.async_get(ALARM)
    assert registered is not None
    assert registered.unique_id == f"{entry.entry_id}_alarm"
    assert registered.entity_category is None
    pump = device_registry.async_get_device_by_identifier((DOMAIN, entry.entry_id), entry.entry_id)
    assert pump is not None
    assert registered.device_id == pump.id


@pytest.mark.parametrize(
    "address",
    [
        66,  # heat pump unit: sum alarm
        34,  # heat pump unit: outdoor sensor alarm
        24,  # heating: system supply low temperature alarm
        47,  # cooling: supply line sensor alarm
    ],
)
async def test_is_on_while_any_alarm_input_is(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
    address: int,
) -> None:
    await setup(hass, entry)

    pump_unit.discrete[address] = True
    await refresh(hass, freezer)
    assert hass.states.get(ALARM).state == STATE_ON  # type: ignore[union-attr]

    pump_unit.discrete[address] = False
    await refresh(hass, freezer)
    assert hass.states.get(ALARM).state == STATE_OFF  # type: ignore[union-attr]


async def test_ignores_the_alarms_of_a_part_the_pump_lacks(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.discrete[76] = True  # pool return line sensor alarm; the pool is off (coil 28)

    await setup(hass, entry)

    assert hass.states.get(ALARM).state == STATE_OFF  # type: ignore[union-attr]


async def test_is_unavailable_while_the_alarm_inputs_fail_to_refresh(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(0, ServerDeviceBusyError(), register_type="discrete")

    await refresh(hass, freezer)

    assert hass.states.get(ALARM).state == STATE_UNAVAILABLE  # type: ignore[union-attr]
