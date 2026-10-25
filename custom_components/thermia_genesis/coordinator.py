"""The coordinator that reads the whole pump."""

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, override

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection.exceptions import ModbusError
from modbus_connection.model import UpdateReport

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from thermia_genesis import ThermiaGenesis

_LOGGER = logging.getLogger(__name__)

# A full read takes about 0.4 s; homeassistant.update_entity refreshes on demand.
UPDATE_INTERVAL = timedelta(seconds=30)

type ThermiaGenesisConfigEntry = ConfigEntry[ThermiaGenesisCoordinator]


class ThermiaGenesisCoordinator(DataUpdateCoordinator[UpdateReport]):
    """Read every register of the pump; the report names the register spaces that failed."""

    config_entry: ThermiaGenesisConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ThermiaGenesisConfigEntry, pump: ThermiaGenesis
    ) -> None:
        """Poll ``pump`` for ``entry``."""
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=entry.title, update_interval=UPDATE_INTERVAL
        )
        self.pump = pump
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

    def _log_changes(self, report: UpdateReport) -> None:
        """Log a register space when it starts failing and when it answers again."""
        for name, error in report.failed.items():
            if name not in self._failing:
                _LOGGER.warning(
                    "%s: %s failed to refresh and keeps its previous values: %s",
                    self.name,
                    name,
                    error,
                )
        for name in self._failing - set(report.failed):
            _LOGGER.info("%s: %s is available again", self.name, name)
        self._failing = set(report.failed)
