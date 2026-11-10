"""The coordinator that reads the whole pump."""

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection.exceptions import ModbusError
from modbus_connection.model import UpdateReport
from thermia_genesis import ThermiaGenesis

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from modbus_connection import ModbusUnit
    from thermia_genesis.subsystem import Field, Subsystem

_LOGGER = logging.getLogger(__name__)

# A full read takes about 0.4 s; homeassistant.update_entity refreshes on demand.
UPDATE_INTERVAL = timedelta(seconds=30)

type ThermiaGenesisConfigEntry = ConfigEntry[ThermiaGenesisCoordinator]


class ThermiaGenesisCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Read every register of the pump; the report names the register spaces that failed."""

    config_entry: ThermiaGenesisConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ThermiaGenesisConfigEntry, unit: ModbusUnit
    ) -> None:
        """Poll the pump on ``unit`` for ``entry``."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=entry.title, update_interval=UPDATE_INTERVAL
        )
        # Kept for the diagnostics, which read the whole pump again.
        self.unit = unit
        self.pump = ThermiaGenesis(unit)
        self._failing: set[str] = set()

    @override
    async def _async_update_data(self) -> UpdateReport:
        try:
            report = await self.pump.async_update()
        except ModbusError as err:
            # A dead link or a timeout; a failure within one register space is in the report.
            raise UpdateFailed(translation_domain=DOMAIN, translation_key="update_failed") from err
        if not report.updated:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="no_register_space_answered"
            ) from ExceptionGroup("every register space failed", list(report.failed.values()))
        self._log_changes(report)
        return report

    async def async_write[T](self, subsystem: Subsystem, field: Field[T], value: T) -> None:
        """Write ``value`` to ``subsystem``'s ``field``, then ask for a read-back.

        The entities show what the pump accepted, which the read after the write returns;
        writes in a burst share one read. Raises ``ServiceValidationError`` for a value the
        library refuses (``ValueError``), and ``HomeAssistantError`` when the pump doesn't
        take the write. A ``TypeError`` (a value of the wrong type) or an ``AttributeError``
        (a read-only field) is an integration bug and propagates.
        """
        try:
            await subsystem.write(field, value)
        except ValueError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_value",
                translation_placeholders={"error": str(err)},
            ) from err
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": f"{type(err).__name__}: {err}"},
            ) from err
        await self.async_request_refresh()

    def _log_changes(self, report: UpdateReport) -> None:
        """Log a register space when it starts failing and when it answers again."""
        for name, error in report.failed.items():
            if name not in self._failing:
                _LOGGER.warning(
                    "%s: %s failed to refresh; its entities are unavailable: %s",
                    self.name,
                    name,
                    error,
                )
        for name in self._failing - set(report.failed):
            _LOGGER.info("%s: %s is available again", self.name, name)
        self._failing = set(report.failed)
