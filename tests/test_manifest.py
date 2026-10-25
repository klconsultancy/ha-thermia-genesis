import json
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.loader import async_get_custom_components

from custom_components.thermia_genesis.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

ROOT = Path(__file__).parent.parent
INTEGRATION = ROOT / "custom_components" / DOMAIN


async def test_home_assistant_finds_the_integration(hass: HomeAssistant) -> None:
    integration = (await async_get_custom_components(hass))[DOMAIN]

    assert integration.name == "Thermia Genesis"
    assert integration.dependencies == ["modbus"]
    assert integration.config_flow is True


def test_requires_the_library_version_it_is_developed_with() -> None:
    # Dependabot bumps pyproject.toml; Home Assistant installs what the manifest lists.
    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert manifest["requirements"] == pyproject["project"]["dependencies"]


def keys(strings: dict[str, Any], prefix: str = "") -> set[str]:
    found: set[str] = set()
    for key, value in strings.items():
        path = f"{prefix}{key}"
        found |= keys(value, f"{path}.") if isinstance(value, dict) else {path}
    return found


@pytest.mark.parametrize("language", ["en", "nl"])
def test_translation_has_every_string(language: str) -> None:
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    translation = json.loads(
        (INTEGRATION / "translations" / f"{language}.json").read_text(encoding="utf-8")
    )

    assert keys(translation) == keys(strings)
