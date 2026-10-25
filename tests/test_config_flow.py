from typing import TYPE_CHECKING

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusTcpParams
from modbus_connection.exceptions import IllegalDataAddressError, ModbusConnectionError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from homeassistant.core import HomeAssistant
    from modbus_connection.mock import MockModbusUnit

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

USER_INPUT = {CONF_HOST: "10.64.30.14", CONF_PORT: 502}


async def test_creates_an_entry_for_a_reachable_pump(
    hass: HomeAssistant, temporary_unit: MagicMock
) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Thermia Genesis"
    assert result["data"] == {CONF_HOST: "10.64.30.14", CONF_PORT: 502, CONF_UNIT_ID: 1}
    temporary_unit.assert_called_once_with(hass, ModbusTcpParams(host="10.64.30.14", port=502), 1)


async def test_port_defaults_to_502(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    schema = result["data_schema"]
    assert schema is not None
    assert schema({CONF_HOST: "pump"}) == {CONF_HOST: "pump", CONF_PORT: 502}


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (ModbusConnectionError("refused"), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
        (HomeAssistantError("in use with different link settings"), "connection_in_use"),
        (RuntimeError("bug"), "unknown"),
    ],
)
async def test_shows_an_error_and_recovers(
    hass: HomeAssistant, temporary_unit: MagicMock, error: Exception, reason: str
) -> None:
    get_temporary_unit = temporary_unit.side_effect
    temporary_unit.side_effect = error
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": reason}

    temporary_unit.side_effect = get_temporary_unit
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_cannot_connect_when_the_pump_does_not_answer(
    hass: HomeAssistant, temporary_unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del temporary_unit
    pump_unit.fail_requests(ModbusConnectionError("no answer"))
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["errors"] == {"base": "cannot_connect"}


async def test_cannot_connect_without_a_firmware_version(
    hass: HomeAssistant, temporary_unit: MagicMock, pump_unit: MockModbusUnit
) -> None:
    del temporary_unit
    for address in (311, 312, 313):
        pump_unit.fail_read(address, IllegalDataAddressError(), register_type="input")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["errors"] == {"base": "cannot_connect"}


async def test_aborts_for_a_pump_already_configured(
    hass: HomeAssistant, temporary_unit: MagicMock
) -> None:
    MockConfigEntry(domain=DOMAIN, data={**USER_INPUT, CONF_UNIT_ID: 1}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    temporary_unit.assert_not_called()


async def test_reconfigure_moves_the_entry_to_a_new_address(
    hass: HomeAssistant, temporary_unit: MagicMock
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={**USER_INPUT, CONF_UNIT_ID: 1})
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.64.30.20", CONF_PORT: 5020}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data == {CONF_HOST: "10.64.30.20", CONF_PORT: 5020, CONF_UNIT_ID: 1}
    temporary_unit.assert_called_once_with(hass, ModbusTcpParams(host="10.64.30.20", port=5020), 1)


async def test_reconfigure_suggests_the_current_address(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: "pump", CONF_PORT: 5020, CONF_UNIT_ID: 1}
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)

    schema = result["data_schema"]
    assert schema is not None
    suggested = {
        str(key): key.description["suggested_value"]
        for key in schema.schema
        if key.description is not None
    }
    assert suggested == {CONF_HOST: "pump", CONF_PORT: 5020}


async def test_reconfigure_keeps_the_same_address(
    hass: HomeAssistant, temporary_unit: MagicMock
) -> None:
    del temporary_unit
    entry = MockConfigEntry(domain=DOMAIN, data={**USER_INPUT, CONF_UNIT_ID: 1})
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["reason"] == "reconfigure_successful"


async def test_reconfigure_aborts_for_an_address_of_another_entry(
    hass: HomeAssistant, temporary_unit: MagicMock
) -> None:
    MockConfigEntry(domain=DOMAIN, data={**USER_INPUT, CONF_UNIT_ID: 1}).add_to_hass(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: "other", CONF_PORT: 502, CONF_UNIT_ID: 1}
    )
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    temporary_unit.assert_not_called()


async def test_reconfigure_shows_an_error_and_recovers(
    hass: HomeAssistant, temporary_unit: MagicMock
) -> None:
    get_temporary_unit = temporary_unit.side_effect
    temporary_unit.side_effect = ModbusConnectionError("refused")
    entry = MockConfigEntry(domain=DOMAIN, data={**USER_INPUT, CONF_UNIT_ID: 1})
    entry.add_to_hass(hass)
    result = await entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.64.30.20", CONF_PORT: 502}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    temporary_unit.side_effect = get_temporary_unit
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.64.30.20", CONF_PORT: 502}
    )

    assert result["reason"] == "reconfigure_successful"
