"""Selects: the writable enum settings, such as the operational mode."""

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.components.select.const import ATTR_OPTIONS
from homeassistant.components.select.const import DOMAIN as SELECT_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_OPTION,
    CONF_HOST,
    CONF_PORT,
    SERVICE_SELECT_OPTION,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from modbus_connection.exceptions import ServerDeviceBusyError, ServerDeviceFailureError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit

MODE = "select.thermia_genesis_operational_mode"


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


def mode(hass: HomeAssistant) -> State:
    found = hass.states.get(MODE)
    assert found is not None
    return found


async def select(hass: HomeAssistant, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: MODE, ATTR_OPTION: option},
        blocking=True,
    )


async def test_shows_the_operational_mode(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await setup(hass, entry)

    state = mode(hass)
    assert state.state == "on_auto"
    assert state.attributes[ATTR_OPTIONS] == ["off", "standby", "on_auto"]


async def test_sets_the_operational_mode(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await select(hass, "standby")

    assert pump_unit.holding[0] == 2
    assert mode(hass).state == "standby"


async def test_refuses_an_option_it_lacks(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await select(hass, "boost")

    assert pump_unit.holding[0] == 3


async def test_reports_a_pump_that_fails_the_write(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)
    pump_unit.fail_write(0, ServerDeviceFailureError(5))

    with pytest.raises(HomeAssistantError) as raised:
        await select(hass, "off")

    assert raised.value.translation_key == "write_failed"


async def test_reads_unknown_for_a_value_the_library_does_not_know(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.holding[0] = 7

    await setup(hass, entry)

    assert mode(hass).state == STATE_UNKNOWN


async def test_is_unavailable_while_the_holding_registers_fail(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(0, ServerDeviceBusyError(), register_type="holding")

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert mode(hass).state == STATE_UNAVAILABLE


async def test_sits_on_the_main_device_and_is_enabled(
    hass: HomeAssistant, entry: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    await setup(hass, entry)

    entity = entity_registry.async_get(MODE)
    assert entity is not None
    assert entity.unique_id == f"{entry.entry_id}_status_operational_mode"
    assert entity.translation_key == "operational_mode"
    assert not entity.disabled


async def test_an_entry_from_before_the_select_drops_the_sensor_it_replaces(
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
    unique_id = f"{entry.entry_id}_status_operational_mode"
    entity_registry.async_get_or_create("sensor", DOMAIN, unique_id, config_entry=entry)

    await setup(hass, entry)

    assert entity_registry.async_get_entity_id("sensor", DOMAIN, unique_id) is None
