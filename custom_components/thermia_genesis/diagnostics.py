"""Diagnostics: the library's dump of the pump, as `thermia-genesis dump` writes it."""

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST
from modbus_connection.exceptions import ModbusError
from thermia_genesis.cli import dump

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import ThermiaGenesisConfigEntry

# The pump's address on the network.
TO_REDACT = {CONF_HOST}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,  # noqa: ARG001
    entry: ThermiaGenesisConfigEntry,
) -> dict[str, Any]:
    """Read the whole pump again, raw and decoded, so a report can become a test fixture."""
    coordinator = entry.runtime_data
    try:
        pump: dict[str, Any] = await dump(coordinator.unit)
    except ModbusError as err:
        # A dropped link or a timeout; the rest still helps.
        pump = {"error": str(err)}
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "failed": {name: str(err) for name, err in coordinator.data.failed.items()},
        },
        "dump": pump,
    }
