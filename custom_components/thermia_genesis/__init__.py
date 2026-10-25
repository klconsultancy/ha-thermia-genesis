"""The Thermia Genesis integration."""

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from modbus_connection import ModbusTcpParams
from thermia_genesis import ThermiaGenesis

from .const import CONF_UNIT_ID, DOMAIN, MANUFACTURER, MODEL, PARTS
from .coordinator import ThermiaGenesisConfigEntry, ThermiaGenesisCoordinator

PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> bool:
    """Set up a pump from a config entry."""
    try:
        unit = async_get_unit(
            hass,
            entry,
            ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
            entry.data[CONF_UNIT_ID],
        )
    except HomeAssistantError as err:
        # Another integration holds the address with other link settings; retrying won't help.
        raise ConfigEntryError(
            translation_domain=DOMAIN, translation_key="connection_in_use"
        ) from err

    coordinator = ThermiaGenesisCoordinator(hass, entry, ThermiaGenesis(unit))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    _async_update_devices(hass, entry)
    _async_update_firmware_issue(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


@callback
def _async_update_devices(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> None:
    """Register the pump and a device per part it has; drop the parts it no longer has."""
    pump = entry.runtime_data.pump
    registry = dr.async_get(hass)
    firmware = pump.firmware_version
    main = registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=entry.title,
        sw_version=None if firmware is None else str(firmware),
    )
    wanted = {main.id}
    for part in PARTS:
        if getattr(pump, part) is None:
            continue
        device = registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{entry.entry_id}_{part}")},
            manufacturer=MANUFACTURER,
            translation_key=part,
            via_device_id=main.id,
        )
        wanted.add(device.id)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        if device.id not in wanted:
            registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)


@callback
def _async_update_firmware_issue(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> None:
    """Warn while the pump runs a firmware the register map isn't written for."""
    issue_id = f"unsupported_firmware_{entry.entry_id}"
    firmware = entry.runtime_data.pump.firmware_version
    if firmware is None or firmware.supported:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="unsupported_firmware",
        translation_placeholders={"title": entry.title, "version": str(firmware)},
    )
