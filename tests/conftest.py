"""Fixtures for the Thermia Genesis tests."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from homeassistant.core import HomeAssistant
    from modbus_connection import ModbusTcpParams, ModbusUnit
    from modbus_connection.mock import MockModbusUnit

# A register dump of the reference pump, copied from the library's tests/fixtures.
REFERENCE_PUMP: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "calibra7-17.1.11.json").read_text(encoding="utf-8")
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load custom_components/ in every test."""


@pytest.fixture
def pump_unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """A mock unit that answers like the reference pump."""
    stores: dict[str, dict[int, Any]] = {
        "coil": mock_modbus_unit.coil,
        "discrete": mock_modbus_unit.discrete,
        "input": mock_modbus_unit.input,
        "holding": mock_modbus_unit.holding,
    }
    for space, registers in REFERENCE_PUMP["registers"].items():
        for address, value in registers.items():
            stores[space][int(address)] = value
    return mock_modbus_unit


@pytest.fixture
def temporary_unit(pump_unit: MockModbusUnit) -> Iterator[MagicMock]:
    """Serve the pump to the config flow in place of the modbus integration's unit."""

    @asynccontextmanager
    async def get_temporary_unit(
        hass: HomeAssistant,  # noqa: ARG001
        params: ModbusTcpParams,  # noqa: ARG001
        unit_id: int,  # noqa: ARG001
    ) -> AsyncIterator[ModbusUnit]:
        yield pump_unit

    with patch(
        "custom_components.thermia_genesis.config_flow.async_get_temporary_unit",
        side_effect=get_temporary_unit,
    ) as mock:
        yield mock


@pytest.fixture
def unit(pump_unit: MockModbusUnit) -> Iterator[MagicMock]:
    """Serve the pump to the entry's setup in place of the modbus integration's unit."""
    with patch("custom_components.thermia_genesis.async_get_unit", return_value=pump_unit) as mock:
        yield mock


@pytest.fixture
def mock_setup_entry() -> Iterator[AsyncMock]:
    """Keep a created entry from being set up."""
    with patch("custom_components.thermia_genesis.async_setup_entry", return_value=True) as mock:
        yield mock
