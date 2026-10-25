from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from modbus_connection import ModbusTcpParams
from modbus_connection.exceptions import (
    IllegalDataAddressError,
    ModbusConnectionError,
    ServerDeviceBusyError,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from modbus_connection.mock import MockModbusUnit


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "10.64.30.14", CONF_PORT: 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    return entry


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def setup_polling(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up with a listener in place of an entity: the coordinator polls only for one."""
    await setup(hass, entry)
    entry.async_on_unload(entry.runtime_data.async_add_listener(lambda: None))


async def wait(hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float) -> None:
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def next_update(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    # The coordinator adds up to a second of jitter to its interval.
    await wait(hass, freezer, 31)


def devices(hass: HomeAssistant, entry: MockConfigEntry) -> dict[str, dr.DeviceEntry]:
    """The entry's devices by the identifier after the entry id."""
    found = {}
    for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id):
        ((_, identifier),) = device.identifiers
        found[identifier.removeprefix(entry.entry_id).removeprefix("_")] = device
    return found


async def test_sets_up_on_the_unit_of_the_modbus_integration(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock
) -> None:
    await setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    unit.assert_called_once_with(hass, entry, ModbusTcpParams(host="10.64.30.14", port=502), 1)


async def test_creates_the_pump_and_a_device_per_present_part(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock
) -> None:
    del unit
    await setup(hass, entry)

    found = devices(hass, entry)
    pump = found.pop("")
    assert (pump.name, pump.manufacturer, pump.model, pump.sw_version) == (
        "Thermia Genesis",
        "Thermia",
        "Genesis",
        "17.1.11",
    )
    # The reference pump has passive cooling and none of the other optional parts.
    assert set(found) == {"heat_pump", "heat", "tap_water", "cooling"}
    assert {part: device.name for part, device in found.items()} == {
        "heat_pump": "Heat pump unit",
        "heat": "Heating",
        "tap_water": "Tap water",
        "cooling": "Cooling",
    }
    for device in found.values():
        assert device.via_device_id == pump.id
        assert device.manufacturer == "Thermia"


async def test_removes_the_device_of_a_part_the_pump_no_longer_has(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del unit
    await setup(hass, entry)
    await hass.config_entries.async_unload(entry.entry_id)
    pump_unit.coil[33] = False  # passive cooling disabled

    await setup(hass, entry)

    assert "cooling" not in devices(hass, entry)


async def test_retries_while_the_pump_does_not_answer(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del unit
    pump_unit.fail_requests(ModbusConnectionError("no answer"))

    await setup(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_fails_when_the_address_is_in_use_with_other_settings(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock
) -> None:
    unit.side_effect = HomeAssistantError("in use with different link settings")

    await setup(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert entry.reason is not None


async def test_raises_a_repair_issue_for_an_unsupported_firmware(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del unit
    pump_unit.input[311] = 18  # major version

    await setup(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    issue = ir.async_get(hass).async_get_issue(DOMAIN, f"unsupported_firmware_{entry.entry_id}")
    assert issue is not None
    assert issue.severity is ir.IssueSeverity.WARNING
    assert not issue.is_fixable
    assert issue.translation_key == "unsupported_firmware"
    assert issue.translation_placeholders == {"title": "Thermia Genesis", "version": "18.1.11"}


async def test_clears_the_repair_issue_once_the_firmware_is_supported(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del unit
    pump_unit.input[311] = 18
    await setup(hass, entry)
    await hass.config_entries.async_unload(entry.entry_id)
    pump_unit.input[311] = 17

    await setup(hass, entry)

    issues = ir.async_get(hass)
    assert issues.async_get_issue(DOMAIN, f"unsupported_firmware_{entry.entry_id}") is None


async def test_unloads(hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock) -> None:
    del unit
    await setup(hass, entry)

    assert await hass.config_entries.async_unload(entry.entry_id)

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_updates_every_30_seconds(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    unit: MagicMock,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    del unit
    await setup_polling(hass, entry)
    reads = len(pump_unit.read_events)

    # Scheduled from a whole second of the loop clock: between 29 and 31 seconds from now.
    await wait(hass, freezer, 28)
    assert len(pump_unit.read_events) == reads

    await wait(hass, freezer, 3)
    assert len(pump_unit.read_events) > reads


async def test_update_fails_when_the_pump_stops_answering(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    unit: MagicMock,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    del unit
    await setup_polling(hass, entry)
    pump_unit.fail_requests(ModbusConnectionError("no answer"))

    await next_update(hass, freezer)

    assert not entry.runtime_data.last_update_success
    assert entry.state is ConfigEntryState.LOADED


async def test_update_fails_when_no_register_space_answers(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    unit: MagicMock,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    del unit
    await setup_polling(hass, entry)
    pump_unit.fail_requests(ServerDeviceBusyError())

    await next_update(hass, freezer)

    assert not entry.runtime_data.last_update_success


async def test_logs_a_failing_register_space_once_and_its_return(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    unit: MagicMock,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    del unit
    await setup_polling(hass, entry)
    pump_unit.fail_read(0, ServerDeviceBusyError(), register_type="holding")

    for _ in range(2):
        await next_update(hass, freezer)

    assert entry.runtime_data.last_update_success
    assert caplog.text.count("holding_registers failed to refresh") == 1

    pump_unit.fail_read(0, None, register_type="holding")
    await next_update(hass, freezer)

    assert caplog.text.count("holding_registers is available again") == 1


async def test_leaves_out_the_firmware_the_pump_does_not_report(
    hass: HomeAssistant, entry: MockConfigEntry, unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del unit
    for address in (311, 312, 313):
        pump_unit.fail_read(address, IllegalDataAddressError(), register_type="input")

    await setup(hass, entry)

    assert devices(hass, entry)[""].sw_version is None
    assert not ir.async_get(hass).issues
