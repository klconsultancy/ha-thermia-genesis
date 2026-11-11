"""The Thermia Genesis integration."""

from homeassistant.components.modbus import async_get_unit
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryError, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import UNDEFINED
from modbus_connection import ModbusTcpParams

from .const import CONF_UNIT_ID, DOMAIN, MANUFACTURER, MODEL, PARTS
from .coordinator import ThermiaGenesisConfigEntry, ThermiaGenesisCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.WATER_HEATER,
]


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

    coordinator = ThermiaGenesisCoordinator(hass, entry, unit)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    _async_update_devices(hass, entry)
    _async_update_firmware_issue(hass, entry)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> bool:
    """Bring an entry from an older minor version of the integration up to date.

    Home Assistant calls this only for an older version and refuses a newer one itself.
    Each step removes entities, which is safe to repeat, so the steps need no guard.
    """
    # 1.2 and 1.3 (0.3.0): the writable entities replace the sensors of the fields they
    # write (1.2), and the climate moved to the main device (1.3).
    _async_remove_entities(
        hass,
        entry,
        [
            (Platform.SENSOR, "heat_comfort_wheel_setting"),
            (Platform.BINARY_SENSOR, "heat_pump_enable_heat"),
            (Platform.BINARY_SENSOR, "heat_pump_reset_all_alarms"),
            (Platform.SENSOR, "status_operational_mode"),
            (Platform.SENSOR, "heat_pump_power_consumption_control_mode"),
            (Platform.SENSOR, "heat_pump_input_power_limit"),
            (Platform.SENSOR, "tap_water_start_temperature"),
            (Platform.SENSOR, "tap_water_stop_temperature"),
            (Platform.BINARY_SENSOR, "heat_pump_enable_tap_water"),
            # 1.3: the climate of 0.3.0-rc.1, on the heating device; now on the main one.
            (Platform.CLIMATE, "heat_climate"),
        ],
    )
    hass.config_entries.async_update_entry(entry, minor_version=3)
    return True


@callback
def _async_remove_entities(
    hass: HomeAssistant, entry: ThermiaGenesisConfigEntry, entities: list[tuple[Platform, str]]
) -> None:
    """Remove ``entry``'s entities, given as platform and unique id without the entry id."""
    registry = er.async_get(hass)
    for platform, key in entities:
        unique_id = f"{entry.entry_id}_{key}"
        if entity_id := registry.async_get_entity_id(platform, DOMAIN, unique_id):
            registry.async_remove(entity_id)


async def async_unload_entry(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: ThermiaGenesisConfigEntry) -> None:
    """Drop the entry's repair issue along with the entry."""
    ir.async_delete_issue(hass, DOMAIN, _firmware_issue_id(entry))


def _firmware_issue_id(entry: ThermiaGenesisConfigEntry) -> str:
    return f"unsupported_firmware_{entry.entry_id}"


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
        # A read that missed the firmware keeps the version registered before.
        sw_version=UNDEFINED if firmware is None else str(firmware),
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
    issue_id = _firmware_issue_id(entry)
    firmware = entry.runtime_data.pump.firmware_version
    if firmware is None:
        return  # unknown: keep the issue as it is
    if firmware.supported:
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
