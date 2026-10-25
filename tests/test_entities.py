"""The entities as Home Assistant shows them, on the reference pump."""

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT, STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.helpers import entity_registry as er
from modbus_connection.exceptions import IllegalDataAddressError, ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    snapshot_platform,
)

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from modbus_connection.mock import MockModbusUnit
    from syrupy.assertion import SnapshotAssertion


@pytest.fixture
def entry(hass: HomeAssistant, unit: MagicMock) -> MockConfigEntry:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "10.64.30.14", CONF_PORT: 502, CONF_UNIT_ID: 1},
        entry_id="01JTHERMIAGENESIS000000000",
    )
    entry.add_to_hass(hass)
    return entry


def state(hass: HomeAssistant, entity_id: str) -> str:
    found = hass.states.get(entity_id)
    assert found is not None, entity_id
    return found.state


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize("platform", [Platform.SENSOR, Platform.BINARY_SENSOR])
async def test_entities(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
    platform: Platform,
) -> None:
    with patch("custom_components.thermia_genesis.PLATFORMS", [platform]):
        await setup(hass, entry)

    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)


async def test_enabled_by_default(
    hass: HomeAssistant, entry: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    await setup(hass, entry)

    enabled = sorted(
        entity.entity_id
        for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if not entity.disabled
    )
    assert enabled == [
        "binary_sensor.heat_pump_unit_compressor",
        "binary_sensor.heat_pump_unit_external_additional_heater",
        "sensor.heat_pump_unit_brine_in_temperature",
        "sensor.heat_pump_unit_brine_out_temperature",
        "sensor.heat_pump_unit_compressor_gear",
        "sensor.heat_pump_unit_compressor_operating_hours",
        "sensor.heat_pump_unit_compressor_speed",
        "sensor.heat_pump_unit_condenser_in_temperature",
        "sensor.heat_pump_unit_condenser_out_temperature",
        "sensor.heat_pump_unit_discharge_pipe_temperature",
        "sensor.heat_pump_unit_heat_output",
        "sensor.heat_pump_unit_immersion_heater_step",
        "sensor.heat_pump_unit_outdoor_temperature",
        "sensor.heat_pump_unit_power_consumption",
        "sensor.heat_pump_unit_room_temperature",
        "sensor.thermia_genesis_operational_mode",
        "sensor.thermia_genesis_running_demand_1",
    ]


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_a_failing_register_space_makes_only_its_entities_unavailable(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(0, ServerDeviceBusyError(), register_type="holding")

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert state(hass, "sensor.thermia_genesis_operational_mode") == STATE_UNAVAILABLE
    assert state(hass, "sensor.thermia_genesis_running_demand_1") == "no_demand"


async def test_an_unknown_enum_value_reads_as_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.input[1] = 0  # no Demand

    await setup(hass, entry)

    assert state(hass, "sensor.thermia_genesis_running_demand_1") == STATE_UNKNOWN


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_a_refused_field_reads_as_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_read(2, IllegalDataAddressError(), register_type="input")

    await setup(hass, entry)

    assert state(hass, "binary_sensor.thermia_genesis_no_demand_running") == STATE_UNKNOWN
