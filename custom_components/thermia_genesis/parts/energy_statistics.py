"""Energy statistics: what the display shows per circuit for two 12-month periods.

No protocol edition lists these registers; the library decoded them against the display
of a Calibra 17.1. Both periods roll per month, so a value can drop, and a pump without
them reads 0. So they are all disabled and stay out of the long-term statistics
(docs/design.md).
"""

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import UnitOfEnergy

from ..descriptions import Sensor, ThermiaGenesisSensorEntityDescription

CIRCUITS = ("heating", "tap_water")
PERIODS = ("months_1_to_12", "months_13_to_24")
ENERGIES = ("aux_heater", "consumed", "delivered", "natural_source")


def energy(key: str) -> Sensor:
    """Describe an energy over a 12-month period in kWh; it is no counter."""
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        entity_registry_enabled_default=False,
    )


def cop(key: str) -> Sensor:
    """Describe the COP over a 12-month period."""
    return ThermiaGenesisSensorEntityDescription(
        key=key,
        translation_key=key,
        suggested_display_precision=1,
        entity_registry_enabled_default=False,
    )


SENSORS: tuple[Sensor, ...] = tuple(
    description
    for period in PERIODS
    for circuit in CIRCUITS
    for description in (
        *(energy(f"{circuit}_{quantity}_{period}") for quantity in ENERGIES),
        cop(f"{circuit}_cop_{period}"),
    )
)
