from typing import TYPE_CHECKING

from homeassistant.loader import async_get_custom_components

from custom_components.thermia_genesis.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


async def test_home_assistant_finds_the_integration(hass: HomeAssistant) -> None:
    integration = (await async_get_custom_components(hass))[DOMAIN]

    assert integration.name == "Thermia Genesis"
    assert integration.dependencies == ["modbus"]
