"""Writing a field to the pump through the coordinator."""

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.update_coordinator import REQUEST_REFRESH_DEFAULT_COOLDOWN
from modbus_connection.exceptions import ModbusConnectionError, ServerDeviceFailureError
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from thermia_genesis.v17_1.heat import Heat
from thermia_genesis.v17_1.heat_pump_unit import HeatPumpUnit

from custom_components.thermia_genesis.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from freezegun.api import FrozenDateTimeFactory
    from homeassistant.core import HomeAssistant
    from modbus_connection.mock import MockModbusUnit

    from custom_components.thermia_genesis.coordinator import ThermiaGenesisCoordinator


@pytest.fixture
async def coordinator(hass: HomeAssistant, unit: MagicMock) -> ThermiaGenesisCoordinator:  # noqa: ARG001
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Thermia Genesis",
        data={CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator: ThermiaGenesisCoordinator = entry.runtime_data
    return coordinator


async def test_write_reads_back_what_the_pump_accepted(
    coordinator: ThermiaGenesisCoordinator, pump_unit: MockModbusUnit
) -> None:
    await coordinator.async_write(coordinator.pump.heat, Heat.comfort_wheel_setting, 21.5)

    assert pump_unit.holding[5] == 2150
    assert coordinator.pump.heat.comfort_wheel_setting == 21.5


async def test_write_refuses_an_invalid_value(
    coordinator: ThermiaGenesisCoordinator, pump_unit: MockModbusUnit
) -> None:
    with pytest.raises(ServiceValidationError) as raised:
        await coordinator.async_write(coordinator.pump.heat, Heat.comfort_wheel_setting, 45.0)

    assert raised.value.translation_key == "invalid_value"
    assert raised.value.translation_placeholders == {
        "error": "comfort_wheel_setting must be from 10 to 40, got 45.0"
    }
    assert pump_unit.holding[5] == 2200


async def test_write_reports_a_pump_that_fails_the_write(
    coordinator: ThermiaGenesisCoordinator, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_write(9, ServerDeviceFailureError(5), register_type="coil")

    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_write(
            coordinator.pump.heat_pump,
            HeatPumpUnit.enable_heat,
            False,  # noqa: FBT003
        )

    assert not isinstance(raised.value, ServiceValidationError)
    assert raised.value.translation_key == "write_failed"
    assert raised.value.translation_placeholders is not None
    assert raised.value.translation_placeholders["error"].startswith("ServerDeviceFailureError: ")


async def test_write_reports_a_lost_connection(
    coordinator: ThermiaGenesisCoordinator, pump_unit: MockModbusUnit
) -> None:
    pump_unit.fail_write(5, ModbusConnectionError("connection lost"))

    with pytest.raises(HomeAssistantError) as raised:
        await coordinator.async_write(coordinator.pump.heat, Heat.comfort_wheel_setting, 21.5)

    assert raised.value.translation_key == "write_failed"
    assert raised.value.translation_placeholders == {
        "error": "ModbusConnectionError: connection lost"
    }


async def test_write_lets_a_wrong_type_through_as_a_bug(
    coordinator: ThermiaGenesisCoordinator,
) -> None:
    # Home Assistant's platforms coerce values first, so only an integration bug gets here.
    with pytest.raises(TypeError):
        await coordinator.async_write(  # type: ignore[misc]
            coordinator.pump.heat, Heat.comfort_wheel_setting, "21.5"
        )


async def test_writes_in_a_burst_share_one_read_back(
    hass: HomeAssistant,
    coordinator: ThermiaGenesisCoordinator,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    await coordinator.async_write(coordinator.pump.heat, Heat.comfort_wheel_setting, 21.5)
    await coordinator.async_write(coordinator.pump.heat, Heat.comfort_wheel_setting, 21.0)
    assert pump_unit.holding[5] == 2100
    assert coordinator.pump.heat.comfort_wheel_setting == 21.5

    freezer.tick(timedelta(seconds=REQUEST_REFRESH_DEFAULT_COOLDOWN))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert coordinator.pump.heat.comfort_wheel_setting == 21.0


async def test_write_succeeds_when_the_read_back_fails(
    coordinator: ThermiaGenesisCoordinator, pump_unit: MockModbusUnit
) -> None:
    # The link drops right after the pump took the write.
    pump_unit.on_write(lambda _: pump_unit.fail_requests(ModbusConnectionError("lost")))

    await coordinator.async_write(coordinator.pump.heat, Heat.comfort_wheel_setting, 21.5)

    assert pump_unit.holding[5] == 2150
    assert not coordinator.last_update_success


async def test_latest_is_what_was_written_until_the_next_read(
    hass: HomeAssistant,
    coordinator: ThermiaGenesisCoordinator,
    pump_unit: MockModbusUnit,
    freezer: FrozenDateTimeFactory,
) -> None:
    heat = coordinator.pump.heat
    assert coordinator.latest(heat, Heat.comfort_wheel_setting) == 22.0

    await coordinator.async_write(heat, Heat.comfort_wheel_setting, 21.5)
    await coordinator.async_write(heat, Heat.comfort_wheel_setting, 21.0)
    # The read-back of the second write waits for the cooldown.
    assert heat.comfort_wheel_setting == 21.5
    assert coordinator.latest(heat, Heat.comfort_wheel_setting) == 21.0

    pump_unit.holding[5] = 2050  # changed on the display in the meantime
    freezer.tick(timedelta(seconds=REQUEST_REFRESH_DEFAULT_COOLDOWN))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert coordinator.latest(heat, Heat.comfort_wheel_setting) == 20.5


async def test_latest_forgets_a_write_the_pump_failed(
    coordinator: ThermiaGenesisCoordinator, pump_unit: MockModbusUnit
) -> None:
    heat = coordinator.pump.heat
    pump_unit.fail_write(5, ServerDeviceFailureError(5))

    with pytest.raises(HomeAssistantError):
        await coordinator.async_write(heat, Heat.comfort_wheel_setting, 21.5)

    assert coordinator.latest(heat, Heat.comfort_wheel_setting) == 22.0
