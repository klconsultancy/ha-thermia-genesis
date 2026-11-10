"""The button that resets the pump's alarms."""

from typing import TYPE_CHECKING

import pytest
from homeassistant.components.button.const import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.button.const import SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PORT, STATE_UNAVAILABLE
from homeassistant.exceptions import HomeAssistantError
from modbus_connection.exceptions import ModbusConnectionError, ServerDeviceFailureError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit

RESET = "button.thermia_genesis_reset_alarms"


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


async def press(hass: HomeAssistant) -> None:
    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: RESET}, blocking=True
    )


async def test_resets_the_alarms(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[3] = False
    await setup(hass, entry)

    await press(hass)

    assert pump_unit.coil[3] is True


async def test_reports_a_pump_that_fails_the_reset(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)
    pump_unit.fail_write(3, ServerDeviceFailureError(5), register_type="coil")

    with pytest.raises(HomeAssistantError) as raised:
        await press(hass)

    assert raised.value.translation_key == "write_failed"


async def test_is_unavailable_while_the_pump_does_not_answer(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)
    pump_unit.fail_requests(ModbusConnectionError("lost"))

    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    state = hass.states.get(RESET)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE


async def test_sits_on_the_main_device(
    hass: HomeAssistant, entry: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    await setup(hass, entry)

    entity = entity_registry.async_get(RESET)
    assert entity is not None
    assert entity.unique_id == f"{entry.entry_id}_reset_alarms"
    assert not entity.disabled
