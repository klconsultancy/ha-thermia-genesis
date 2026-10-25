# Context

Terms used in code, docs and issues. Pump terms (register space, subsystem, gear, absent
sensor, ...) are defined in the library's
[`CONTEXT.md`](https://github.com/klconsultancy/python-thermia-genesis/blob/main/CONTEXT.md).

**Config entry**
: One configured pump in Home Assistant: its host, port and unit id. Its `entry_id` is the
basis of every unique id, because the pump has no serial number.

**Unit**
: The `ModbusUnit` the `modbus` integration lends to the entry. The integration never opens
or closes the connection itself.

**Coordinator**
: The `DataUpdateCoordinator` that reads the whole pump with one `async_update()` and hands
the result to every entity.

**Main device / sub-device**
: The main device stands for the pump and its controller; each subsystem the pump has is a
sub-device linked to it with `via_device`.

**Entity description**
: The hand-written Home Assistant metadata of one library field: translation key, device
class, state class, entity category and whether it is enabled by default.

**Aggregate alarm**
: The derived binary sensor that is on when any alarm input of the pump is on.
