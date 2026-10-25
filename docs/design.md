# Design

The current design of the Thermia Genesis integration and the reasons behind it. This is a
living document: when a choice changes, edit the relevant section. Git keeps the history.

Terms are defined in [`CONTEXT.md`](../CONTEXT.md). The register map, the decoding and the
detection of optional parts live in the library
[`thermia-genesis`](https://github.com/klconsultancy/python-thermia-genesis); its
[design](https://github.com/klconsultancy/python-thermia-genesis/blob/main/docs/design.md)
explains them. This integration only turns the library's fields into Home Assistant
entities.

## Scope

- Read-only first. Settings become writable (`number`, `select`, `switch`) after the
  library's write API (python-thermia-genesis#19).
- Modbus TCP first. RTU is mostly config-flow work, because the connection comes from Home
  Assistant's `modbus` integration.
- Distributed through HACS first; the target after that is Home Assistant core at the
  Silver quality scale.

## Home Assistant version

- Minimum 2026.10.0 (`hacs.json`). `homeassistant.components.modbus.async_get_unit` exists
  since 2026.9, but 2026.9 ships `modbus-connection` 4.10.0, which lacks the `Device` model
  the library builds on. 2026.10.0 ships 4.12.3, the library's lower bound.
- The library is installed next to the `modbus` integration's exact `modbus-connection`
  pin, so it must accept a wide range; its CI tests the lower bound.
- Python 3.14, Home Assistant's own requirement. Tests run against the Home Assistant
  version that `pytest-homeassistant-custom-component` pins.

## Connection

- The config flow asks host and port (default 502), with selectors and a probatio schema
  like the core `sofar` integration, which uses the same Modbus helpers. The entry data also holds `unit_id: 1`
  (the controller ignores the unit id on TCP), so RTU can be added without migrating data.
- The flow validates the target with `async_get_temporary_unit` by reading the firmware
  version, and shows `cannot_connect` when that fails.
- Setup gets the unit with `async_get_unit(hass, entry, ModbusTcpParams(...), unit_id)`.
  That does no I/O, so a pump that is off doesn't block setup. The `modbus` integration owns
  the connection and reopens it on the next request; the entry is never reloaded because
  the link dropped.
- Both functions raise `HomeAssistantError` when another integration already uses the
  endpoint with different link settings. The config flow and the reconfigure step show the
  error `connection_in_use`; setup raises `ConfigEntryError`, because retrying doesn't
  resolve the conflict.
- A reconfigure step changes host and port in place, so a new IP address keeps the entry
  and with it every entity and its history.

## Identity

- The pump has no serial number or model register, and its MAC address isn't reachable: ARP
  and DHCP discovery only work within one network segment, and behind a Modbus gateway the
  MAC would be the gateway's. So the config entry has no unique id.
- A second entry for the same host and port is refused (`_async_abort_entries_match`).
- Entity unique ids are `f"{entry_id}_{subsystem}_{field}"`, stable for the life of the
  entry.

## Devices

- One main device "Thermia Genesis": manufacturer Thermia, model Genesis, `sw_version` the
  firmware version. The status entities (operational mode, demands) and the aggregate alarm
  belong to it. The user renames it to the actual model.
- One sub-device per subsystem the pump has (heat pump unit, heat, mix valve 1, tap water,
  HGW, cooling, pool, electric meter), linked with `via_device` to the main device, all on
  one level. An optional part the pump doesn't have gets no sub-device.
- Device identifiers are `(DOMAIN, f"{entry_id}_{subsystem}")`.

## Updates

- One `DataUpdateCoordinator` calls `ThermiaGenesis.async_update()` every 30 seconds. The
  interval is not configurable; `homeassistant.update_entity` refreshes on demand. A full
  read takes about 0.4 s.
- A lost connection or a timeout raises `UpdateFailed`, so every entity is unavailable.
- A register space that failed in the `UpdateReport` makes only the entities of that space
  unavailable; the others keep their fresh values.
- A firmware other than 17.1 still loads with the 17.1 map and raises a warning repair
  issue that names the version found.

## Entities

- Every field of the library becomes an entity: one per field, except a flags field, which
  becomes one per member. A hand-written entity description per field (per member for
  flags) sets its translation key, device class, state class, entity category and whether
  it is enabled by default. A test requires that the descriptions cover every library field
  exactly once (every member of a flags field) with a unit that matches the library's.
- Platforms:
  - coils and discrete inputs: `binary_sensor`; alarms get device class `problem`;
  - enums: `sensor` with device class `enum` and translated options;
  - flags: one `binary_sensor` per member;
  - holding registers (settings): `sensor` with entity category `diagnostic` until the
    write API. They then become `number`/`select` entities, and a registry migration
    removes the old sensors.
- State classes: `measurement` for temperatures, power, gears and percentages;
  `total_increasing` for operating hours (device class `duration`) and the electric meter's
  kWh (device class `energy`, usable in the energy dashboard).
- The electric meter reports its energy twice. `kwh_total` (input 83–84, 32-bit) is the
  energy sensor enabled by default: it practically never wraps. Its LSB-first word order
  comes from the community (CJNE #292), not from the protocol document, and the reference
  pump has no meter to confirm it. `meter_value` (input 81, 16-bit) wraps after 65535 kWh,
  which `total_increasing` reads as a reset; it is disabled by default.
- One derived `binary_sensor` "Alarm" (device class `problem`) on the main device is on when
  any alarm input is on, for notifications.
- Enabled by default: the measured temperatures, operational mode, running demand 1,
  compressor gear, speed and operating hours, the auxiliary heater, the tap water top
  temperature, and the electric meter's power and kWh. Everything else (queued demands, PID
  values, flags, settings, individual alarms) is disabled by default.
- Entity names come from translations (`has_entity_name`), in English and Dutch.

## Diagnostics

- The entry's diagnostics hold the raw registers and the decoded values per subsystem, like
  `thermia-genesis dump`, with the host redacted. They are the first thing to ask for in a
  report about another pump or firmware.

## Coexistence

- The older `thermiagenesis` custom integration uses another domain, so both can run side
  by side, each with its own TCP connection. Nothing is migrated from it.

## Tooling and process

- Tests use `pytest-homeassistant-custom-component`, `modbus_connection`'s mock unit and a
  copy of the library's Calibra 7 fixture; entity states are checked with syrupy snapshots.
  An end-to-end test goes through the real `async_get_unit` to an in-process `tmodbus`
  server. Tests never touch a real pump.
- The manifest's requirement on the library equals the dependency in `pyproject.toml`; a
  test keeps them in step, because Dependabot only bumps the latter. The requirements of
  Home Assistant's `modbus` integration are development dependencies pinned to the versions
  of the tested Home Assistant release; Dependabot leaves them alone.
- Every translation has exactly the keys of `strings.json` (a test checks it).
- uv (with a committed `uv.lock`; the project is not a package), ruff (`ALL` rules), mypy
  strict, prek. Strict TDD; CI enforces 100% line and branch coverage and runs hassfest and
  the HACS validation.
- Every change goes through a pull request with a Conventional Commits title. release-please
  turns merged commits into a release PR; merging it tags `vX.Y.Z` and creates the GitHub
  Release HACS installs from. It also bumps the version in `manifest.json`.
- Development happens in the devcontainer, in a git worktree under `.worktrees/<branch>`.
