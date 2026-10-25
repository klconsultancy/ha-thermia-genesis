import json
import re
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import homeassistant
from homeassistant.components import modbus
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


def test_tests_run_on_the_modbus_requirements_of_home_assistant() -> None:
    # Dependabot leaves these pins alone, so a newer homeassistant must fail here.
    manifest = json.loads((Path(modbus.__file__).parent / "manifest.json").read_text("utf-8"))
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert set(manifest["requirements"]) <= set(pyproject["dependency-groups"]["dev"])


REFERENCE = re.compile(r"\[%key:([^%]+)%\]")


def resolve(strings: dict[str, Any], sources: dict[str, Any]) -> dict[str, Any]:
    """Replace each [%key:...%] reference the way Home Assistant builds en.json."""

    def lookup(path: str) -> str:
        value: Any = sources
        for part in path.split("::"):
            value = value[part]
        return REFERENCE.sub(lambda match: lookup(match[1]), value)

    return {
        key: resolve(value, sources)
        if isinstance(value, dict)
        else REFERENCE.sub(lambda match: lookup(match[1]), value)
        for key, value in strings.items()
    }


def test_english_translation_is_the_resolved_strings() -> None:
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    common = json.loads(
        (Path(homeassistant.__file__).parent / "strings.json").read_text(encoding="utf-8")
    )
    english = json.loads((INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8"))

    assert english == resolve(strings, {**common, "component": {DOMAIN: strings}})


def keys(strings: dict[str, Any], prefix: str = "") -> set[str]:
    found: set[str] = set()
    for key, value in strings.items():
        path = f"{prefix}{key}"
        found |= keys(value, f"{path}.") if isinstance(value, dict) else {path}
    return found


def test_dutch_translation_has_every_string() -> None:
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    translation = json.loads((INTEGRATION / "translations" / "nl.json").read_text(encoding="utf-8"))

    assert keys(translation) == keys(strings)
