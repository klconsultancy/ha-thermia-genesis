"""Status: the operational mode and the demands, on the pump's own device."""

from thermia_genesis.v17_1.enums import Demand, OperationalMode, RunningDemands

from custom_components.thermia_genesis.descriptions import (
    BinarySensor,
    Sensor,
    enumeration,
    members,
)

SENSORS: tuple[Sensor, ...] = (
    enumeration("operational_mode", OperationalMode, enabled=True),
    enumeration("running_demand_1", Demand, enabled=True),
    enumeration("running_demand_2", Demand),
    enumeration("running_demand_3", Demand),
    enumeration("queued_demand_1", Demand),
    enumeration("queued_demand_2", Demand),
    enumeration("queued_demand_3", Demand),
    enumeration("queued_demand_4", Demand),
    enumeration("queued_demand_5", Demand),
)

BINARY_SENSORS: tuple[BinarySensor, ...] = members("running_demands", RunningDemands)
