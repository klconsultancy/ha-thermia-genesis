"""The config entry diagnostics: the library's dump of the pump, with the host redacted."""

import json
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from modbus_connection.exceptions import ModbusConnectionError, ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

from .conftest import REFERENCE_PUMP

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from modbus_connection.mock import MockModbusUnit
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

HOST = "10.64.30.14"


@pytest.fixture
def entry(hass: HomeAssistant, unit: MagicMock) -> MockConfigEntry:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: HOST, CONF_PORT: 502, CONF_UNIT_ID: 1},
        entry_id="01JTHERMIAGENESIS000000000",
    )
    entry.add_to_hass(hass)
    return entry


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_hold_the_dump_of_the_pump(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    # The same JSON as `thermia-genesis dump`, so a report can become a test fixture.
    assert diagnostics["dump"] == REFERENCE_PUMP
    assert diagnostics["entry"]["data"] == {
        CONF_HOST: "**REDACTED**",
        CONF_PORT: 502,
        CONF_UNIT_ID: 1,
    }
    assert diagnostics["coordinator"] == {"last_update_success": True, "failed": {}}
    assert HOST not in json.dumps(diagnostics)


async def test_name_the_register_spaces_that_failed_to_refresh(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(0, ServerDeviceBusyError(), register_type="holding")
    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert list(diagnostics["coordinator"]["failed"]) == ["holding_registers"]
    assert list(diagnostics["dump"]["failed"]) == ["holding"]


async def test_say_why_the_dump_is_missing_when_the_link_drops(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(0, ModbusConnectionError("link down"), register_type="holding")

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["dump"] == {"error": "link down"}
    assert diagnostics["entry"]["data"][CONF_HOST] == "**REDACTED**"
