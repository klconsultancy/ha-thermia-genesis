"""The integration over real Modbus TCP, through Home Assistant's modbus integration.

An in-process tmodbus server replays the reference pump and refuses every address the
fixture doesn't hold, like a pump that serves only what it has. Nothing is patched between
the config entry and the socket; no hardware is involved.
"""

import socket
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_OFF
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from tmodbus.exceptions import IllegalDataAddressError
from tmodbus.pdu import (
    ReadCoilsPDU,
    ReadDiscreteInputsPDU,
    ReadHoldingRegistersPDU,
    ReadInputRegistersPDU,
)
from tmodbus.server import AsyncTcpServer, ModbusRequestRouter

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

from .conftest import REFERENCE_PUMP

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

type Request = (
    ReadCoilsPDU | ReadDiscreteInputsPDU | ReadHoldingRegistersPDU | ReadInputRegistersPDU
)


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def router_for(registers: dict[str, dict[str, Any]]) -> ModbusRequestRouter:
    """Serve ``registers`` (a fixture's raw registers); refuse any other address."""
    router = ModbusRequestRouter()

    def serve(space: str) -> Callable[[int, Request], Any]:
        async def handle(_unit_id: int, request: Request) -> list[Any]:
            values = registers.get(space, {})
            addresses = range(request.start_address, request.start_address + request.quantity)
            if any(str(address) not in values for address in addresses):
                raise IllegalDataAddressError(request.function_code)
            return [values[str(address)] for address in addresses]

        return handle

    router.register(ReadCoilsPDU)(serve("coil"))
    router.register(ReadDiscreteInputsPDU)(serve("discrete"))
    router.register(ReadInputRegistersPDU)(serve("input"))
    router.register(ReadHoldingRegistersPDU)(serve("holding"))
    return router


@pytest.fixture
async def reference_pump(socket_enabled: None) -> AsyncIterator[int]:
    """The port of a server that replays the reference pump."""
    del socket_enabled
    port = free_port()
    server = AsyncTcpServer("127.0.0.1", router_for(REFERENCE_PUMP["registers"]), port=port)
    await server.start()
    yield port
    await server.stop()


async def test_reads_the_reference_pump_over_tcp(
    hass: HomeAssistant, hass_client: ClientSessionGenerator, reference_pump: int
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "127.0.0.1", CONF_PORT: reference_pump, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    outdoor = hass.states.get("sensor.heat_pump_unit_outdoor_temperature")
    assert outdoor is not None
    assert float(outdoor.state) == REFERENCE_PUMP["values"]["heat_pump"]["outdoor_temperature"]
    assert hass.states.get("binary_sensor.thermia_genesis_alarm").state == STATE_OFF  # type: ignore[union-attr]
    # Every read stays within the fixture, so the server refused nothing.
    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert diagnostics["dump"] == REFERENCE_PUMP

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED  # type: ignore[comparison-overlap]
