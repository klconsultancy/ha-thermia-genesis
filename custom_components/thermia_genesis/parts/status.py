"""Status: the operational mode and the demands, on the pump's own device."""

from thermia_genesis.v17_1.enums import Demand, RunningDemands

from ..descriptions import (
    BinarySensor,
    Select,
    Sensor,
    choice,
    enumeration,
    members,
)

SENSORS: tuple[Sensor, ...] = (
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

SELECTS: tuple[Select, ...] = (choice("operational_mode", enabled=True),)
