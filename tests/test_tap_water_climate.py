"""The hot water climate: its temperature, the start and stop temperatures, on or off."""

from datetime import timedelta
from typing import TYPE_CHECKING, Any, Literal

import pytest
from homeassistant.components.climate.const import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODE,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ATTR_TARGET_TEMP_STEP,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_PORT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.update_coordinator import REQUEST_REFRESH_DEFAULT_COOLDOWN
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
from modbus_connection.exceptions import IllegalDataAddressError, ServerDeviceBusyError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant, State
    from homeassistant.helpers import entity_registry as er
    from modbus_connection.mock import MockModbusUnit

HOT_WATER = "climate.hot_water"

# Running demands (input 2) with the hot water and the anti-legionella bits.
HOT_WATER_NOW = 1 << 2
ANTI_LEGIONELLA_NOW = 1 << 6


@pytest.fixture
def entry(hass: HomeAssistant, unit: MagicMock) -> MockConfigEntry:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    return entry


async def setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def climate(hass: HomeAssistant) -> State:
    found = hass.states.get(HOT_WATER)
    assert found is not None
    return found


async def read_back(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Let the read after a burst of writes happen."""
    freezer.tick(timedelta(seconds=REQUEST_REFRESH_DEFAULT_COOLDOWN))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def set_range(hass: HomeAssistant, **data: object) -> None:
    await hass.services.async_call(
        CLIMATE_DOMAIN, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: HOT_WATER, **data}, blocking=True
    )


async def test_shows_the_water_and_its_start_and_stop(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    state = climate(hass)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 48.9  # 48.86, shown in tenths
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 45.0
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 55.0
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE


async def test_offers_the_range_the_library_accepts(
    hass: HomeAssistant, entry: MockConfigEntry
) -> None:
    await setup(hass, entry)

    state = climate(hass)
    assert state.attributes[ATTR_MIN_TEMP] == 35
    assert state.attributes[ATTR_MAX_TEMP] == 60
    assert state.attributes[ATTR_TARGET_TEMP_STEP] == 0.5


@pytest.mark.parametrize("demand", [HOT_WATER_NOW, ANTI_LEGIONELLA_NOW])
async def test_heats_while_a_hot_water_demand_runs(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit, demand: int
) -> None:
    pump_unit.input[2] = demand

    await setup(hass, entry)

    assert climate(hass).attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING


async def test_is_off_while_hot_water_is_disabled(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[8] = False

    await setup(hass, entry)

    state = climate(hass)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.OFF


@pytest.mark.parametrize(
    ("low", "high"),
    [
        (56.0, 59.0),  # both up, the start above the old stop
        (38.0, 44.0),  # both down, the stop below the old start
        (47.5, 52.0),  # within the old range
    ],
)
async def test_sets_the_start_and_stop_temperatures(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
    low: float,
    high: float,
) -> None:
    await setup(hass, entry)
    # The start and stop temperatures after each write.
    after: list[tuple[Any, Any]] = []
    pump_unit.on_write(lambda _: after.append((pump_unit.holding[22], pump_unit.holding[23])))

    await set_range(hass, **{ATTR_TARGET_TEMP_LOW: low, ATTR_TARGET_TEMP_HIGH: high})

    assert after[-1] == (round(low * 100), round(high * 100))
    assert all(start < stop for start, stop in after)
    # The second write's read-back comes after the cooldown (docs/design.md, Writes).
    await read_back(hass, freezer)
    state = climate(hass)
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == low
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == high


async def test_sets_the_stop_temperature_alone(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    await set_range(hass, **{ATTR_TARGET_TEMP_LOW: 45.0, ATTR_TARGET_TEMP_HIGH: 57.0})

    assert pump_unit.holding[22] == 4500
    assert pump_unit.holding[23] == 5700


@pytest.mark.parametrize(
    ("low", "high", "translation_key"),
    [
        (55.0, 55.0, "start_not_below_stop"),
        # Home Assistant refuses a low above the high itself.
        (56.0, 50.0, "low_temp_higher_than_high_temp"),
    ],
)
async def test_refuses_a_start_not_below_the_stop(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    low: float,
    high: float,
    translation_key: str,
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError) as raised:
        await set_range(hass, **{ATTR_TARGET_TEMP_LOW: low, ATTR_TARGET_TEMP_HIGH: high})

    assert raised.value.translation_key == translation_key
    assert pump_unit.holding[22] == 4500
    assert pump_unit.holding[23] == 5500


async def test_refuses_a_temperature_out_of_range(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    await setup(hass, entry)

    with pytest.raises(ServiceValidationError):
        await set_range(hass, **{ATTR_TARGET_TEMP_LOW: 45.0, ATTR_TARGET_TEMP_HIGH: 65.0})

    assert pump_unit.holding[23] == 5500


async def test_rounds_the_temperatures_to_the_register(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    hass.config.units = US_CUSTOMARY_SYSTEM
    await setup(hass, entry)

    # 115 °F is 46.111... °C, 130 °F is 54.444... °C.
    await set_range(hass, **{ATTR_TARGET_TEMP_LOW: 115, ATTR_TARGET_TEMP_HIGH: 130})

    assert pump_unit.holding[22] == 4611
    assert pump_unit.holding[23] == 5444


async def test_turns_hot_water_off_and_on(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await setup(hass, entry)

    for mode, coil in ((HVACMode.OFF, False), (HVACMode.HEAT, True)):
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: HOT_WATER, ATTR_HVAC_MODE: mode},
            blocking=True,
        )
        assert pump_unit.coil[8] is coil
        await read_back(hass, freezer)
        assert climate(hass).state == mode


async def test_sets_the_mode_and_the_range_at_once(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.coil[8] = False
    await setup(hass, entry)

    await set_range(
        hass,
        **{ATTR_TARGET_TEMP_LOW: 44.0, ATTR_TARGET_TEMP_HIGH: 54.0, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    assert pump_unit.coil[8] is True
    assert pump_unit.holding[22] == 4400


async def test_reads_unknown_while_a_value_is_unknown(
    hass: HomeAssistant, entry: MockConfigEntry, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_read(2, IllegalDataAddressError(), register_type="input")
    pump_unit.fail_read(8, IllegalDataAddressError(), register_type="coil")

    await setup(hass, entry)

    state = climate(hass)
    assert state.state == STATE_UNKNOWN
    assert ATTR_HVAC_ACTION not in state.attributes


@pytest.mark.parametrize(("space", "address"), [("holding", 22), ("input", 17), ("coil", 8)])
async def test_is_unavailable_while_a_register_space_it_reads_fails(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
    space: Literal["holding", "input", "coil"],
    address: int,
) -> None:
    await setup(hass, entry)
    pump_unit.fail_read(address, ServerDeviceBusyError(), register_type=space)

    freezer.tick(timedelta(seconds=31))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert climate(hass).state == STATE_UNAVAILABLE


async def test_an_entry_from_before_the_climate_drops_the_sensors_it_replaces(
    hass: HomeAssistant, unit: MagicMock, entity_registry: er.EntityRegistry
) -> None:
    del unit
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1},
        minor_version=2,
    )
    entry.add_to_hass(hass)
    replaced = [
        ("sensor", f"{entry.entry_id}_tap_water_start_temperature"),
        ("sensor", f"{entry.entry_id}_tap_water_stop_temperature"),
        ("binary_sensor", f"{entry.entry_id}_heat_pump_enable_tap_water"),
    ]
    for platform, unique_id in replaced:
        entity_registry.async_get_or_create(platform, DOMAIN, unique_id, config_entry=entry)

    await setup(hass, entry)

    assert entry.minor_version == 3
    for platform, unique_id in replaced:
        assert entity_registry.async_get_entity_id(platform, DOMAIN, unique_id) is None
