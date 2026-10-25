"""Config flow for the Thermia Genesis integration."""

import logging
from typing import Any, override

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
from modbus_connection import ModbusTcpParams
from modbus_connection.exceptions import ModbusError
from thermia_genesis import ThermiaGenesis

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

_LOGGER = logging.getLogger(__name__)

TITLE = "Thermia Genesis"


SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)),
            probatio.Coerce(int),
        ),
    }
)


class ThermiaGenesisConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a Thermia Genesis pump reachable over Modbus TCP."""

    VERSION = 1
    MINOR_VERSION = 1

    @override
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask where the pump is and check that it answers."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # The pump has no serial number, so its address identifies it.
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
            )
            if (error := await self._async_validate(user_input)) is None:
                return self.async_create_entry(
                    title=TITLE, data={**user_input, CONF_UNIT_ID: DEFAULT_UNIT_ID}
                )
            errors["base"] = error
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Move the entry to a new address, keeping its entities and their history."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            address = (user_input[CONF_HOST], user_input[CONF_PORT])
            for other in self._async_current_entries(include_ignore=False):
                if other.entry_id != entry.entry_id and (
                    (other.data[CONF_HOST], other.data[CONF_PORT]) == address
                ):
                    return self.async_abort(reason="already_configured")
            if (error := await self._async_validate(user_input)) is None:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or entry.data),
            errors=errors,
        )

    async def _async_validate(self, user_input: dict[str, Any]) -> str | None:
        """Read the pump's firmware version; return the error key if that fails."""
        params = ModbusTcpParams(host=user_input[CONF_HOST], port=user_input[CONF_PORT])
        try:
            async with async_get_temporary_unit(self.hass, params, DEFAULT_UNIT_ID) as unit:
                pump = ThermiaGenesis(unit)
                await pump.async_update()
        except ModbusError, TimeoutError:
            return "cannot_connect"
        except HomeAssistantError:
            # Another integration holds the address with other link settings.
            return "connection_in_use"
        except Exception:
            _LOGGER.exception("Unexpected error while connecting to the pump")
            return "unknown"
        if pump.firmware_version is None:
            return "cannot_connect"
        return None
