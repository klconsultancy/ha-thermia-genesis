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

- Read first, then writes: settings become writable (`climate`, `number`, `select`,
  `switch`) on top of the library's write API (thermia-genesis 0.4.0), field by field as
  the library declares them writable (milestone 0.3.0).
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
  like the core `sofar` integration, which uses the same Modbus helpers. The entry data also
  holds `unit_id: 1` (the controller ignores the unit id on TCP), so RTU can be added
  without migrating data.
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
  entry. An entity that stands for no single field has its own: `{entry_id}_alarm`,
  `{entry_id}_reset_alarms`, `{entry_id}_<part>_climate`.

## Devices

- One main device "Thermia Genesis": manufacturer Thermia, model Genesis, `sw_version` the
  firmware version. The status entities (operational mode, demands) and the aggregate alarm
  belong to it. The user renames it to the actual model.
- One sub-device per subsystem the pump has (heat pump unit, heat, mix valve 1, hot water,
  HGW, cooling, pool, electric meter, energy statistics), linked with `via_device` to the
  main device, all on one level. An optional part the pump doesn't have gets no sub-device.
- The pump's device identifier is `(DOMAIN, entry_id)`, a part's
  `(DOMAIN, f"{entry_id}_{part}")`, with the part named as its attribute on
  `ThermiaGenesis`.
- Setup registers the devices itself, after the first read, so a part's device exists
  before its entities and names its `via_device`. Part names are translated
  (`translation_key`). A part the pump no longer has (detected again on every setup) loses
  its device.

## Updates

- One `DataUpdateCoordinator` calls `ThermiaGenesis.async_update()` every 30 seconds. The
  interval is not configurable; `homeassistant.update_entity` refreshes on demand. A full
  read takes about 0.4 s.
- The coordinator polls only while it has listeners, so only once entities exist.
- A lost connection or a timeout raises `UpdateFailed`, so every entity is unavailable. So
  does an update in which no register space answers.
- A register space that starts failing is logged once as a warning, and once as info when
  it answers again.
- A register space that failed in the `UpdateReport` makes only the entities of that space
  unavailable; the others keep their fresh values.
- A firmware other than 17.1 still loads with the 17.1 map and raises a warning repair
  issue that names the version found. Setup with a supported firmware removes the issue,
  and so does removing the entry. A first read that misses the firmware leaves both the
  issue and the device's software version as they were.
- When the first read fails, setup raises `ConfigEntryNotReady` (through the coordinator's
  first refresh) and Home Assistant retries.

## Writes

- Every write goes through `coordinator.async_write(subsystem, field, value)`, which calls
  the library's `Subsystem.write` and then asks for a refresh (`async_request_refresh`).
  The library leaves a field at its old value until the next read, so the entities show
  what the pump accepted, not what was sent. The first write reads back at once; writes in
  the following 10 seconds share one read after that cooldown.
- An entity validates first: it sets min and max from the library's validator (and options
  for a select), so Home Assistant refuses a bad value in the user's language. Its step is
  a multiple of the register's resolution, and it rounds a value to that resolution.
- A value the library still refuses (`ValueError`) raises `ServiceValidationError` with the
  library's message. A write the pump fails, or a lost connection (`ModbusError`), raises
  `HomeAssistantError` with the error's type and message, so a timeout and a refusal can be
  told apart. Both are translated. A `TypeError` or `AttributeError` (a wrong type, a
  read-only field) can only be an integration bug, so it propagates and is logged as one.
  Nothing retries a write.
- A write that the pump took is a success even when the read-back fails; the entities then
  go unavailable like after any failed update, and the next poll shows the value.
- Tests write to the mock unit only, never to a real pump.

## Entities

- Every field of the library becomes an entity: one per field, except a flags field, which
  becomes one per member. A hand-written entity description per field (per member for
  flags) sets its translation key, device class, state class, entity category and whether
  it is enabled by default. A test requires that the descriptions cover every library field
  exactly once (every member of a flags field) with a unit that matches the library's; a
  field a climate or a button writes counts as theirs (`climate.FIELDS`, `button.FIELDS`).
  Like the library's consistency test, it lists the parts it holds complete; each part's
  pull request adds its part.
- Each part declares its entities in its own module, `parts/<part>.py` (`SENSORS`,
  `BINARY_SENSORS`, `SELECTS`), with the helpers of `descriptions.py` (`temperature`,
  `setting`, `alarm`, `running`, `choice`, ...), so a part reads as one list;
  `parts/__init__.py` registers each part once per platform. The field name is the `key` and the translation key.
- A diagnostic measurement (a count, a version, a point on the heat curve's x axis) and every
  setting have no state class, so they stay out of the long-term statistics; tests enforce
  that settings are diagnostic.
  A key is shared by parts with a field of the same name ("Supply line temperature"); the
  device name tells them apart. Every entity has a translated name, which a test enforces.
- An entity is unavailable while its field's register space fails. A field the pump
  refuses, or an enum value the library doesn't know, reads as unknown.
- Platforms:
  - coils and discrete inputs: `binary_sensor`; alarms get device class `problem`;
  - writable numbers: `number` (`NUMBERS`, with `adjustable`), mode box, category
    `config`, disabled; min and max from the library's `Between`, step its resolution, and a
    value is rounded to that resolution before the write. A test holds every number to a
    writable field with a `Between` and the library's unit;
  - enums: `sensor` with device class `enum` and translated options; a writable enum is a
    `select` (`parts/<part>.py`, `SELECTS`, with `choice`) whose options are the members
    of the library's `MemberOf` validator, as lowercase names with translations. A test
    holds every select to a writable field with a `MemberOf`. A select has category
    `config`, which keeps it off the generated dashboard, where the operational mode's Off
    would be a tap away; the operational mode is enabled, the rest disabled;
  - flags: one `binary_sensor` per member;
  - holding registers (settings): `sensor` with entity category `diagnostic`. As the
    library declares a setting writable, it becomes a `number`, `select`, `switch` or part
    of a `climate` entity (milestone 0.3.0), and the old sensor goes. A config entry
    migration removes it: each release that removes entities raises the entry's minor
    version, so it runs once per entry; 1.2 holds every removal of 0.3.0. Once in core,
    removing an entity would need a deprecation period with a repair issue first.
- Climate "Heating" (enabled, on the heating device, named after it): the room temperature
  (`heat_pump.room_temperature`), the comfort wheel as target (`heat.comfort_wheel_setting`)
  and heating on or off as HVAC mode `heat`/`off` (`heat_pump.enable_heat`). Its min and
  max come from the library's `Between`, falling back to Home Assistant's defaults without
  one. The card steps by 0.5 °C, a multiple of the register's 0.01, so the pump takes every
  step. Any value is rounded to the register's resolution before the write, since Home
  Assistant converts °F to °C without rounding (70 °F is 21.11 °C). The action is
  `defrosting` or `heating` while the running demands hold `DEFROST` or `HEAT`, `idle`
  otherwise, `off` while heating is disabled. A `set_temperature` with an HVAC mode
  validates and writes the mode first. A writing platform has `PARALLEL_UPDATES = 1`. It
  is unavailable while the coils, the holding or the input registers fail, and replaces
  the `comfort_wheel_setting` sensor and the `enable_heat` binary sensor.
- Button "Reset alarms" (enabled, on the main device next to the alarm) writes on to
  `heat_pump.reset_all_alarms` (coil 3) and never off: the reference pump clears the coil
  itself within seconds (python-thermia-genesis errata, 2026-11-10). Whether a reset clears
  an alarm whose cause is still there is not tested. It has no entity category: resetting
  is what a user does after the Alarm, not a setting of the pump. It reads nothing, so it
  is unavailable only while the pump doesn't answer at all, not when one register space
  fails. It replaces the `reset_all_alarms` binary sensor ("Alarm reset pending").
- Power consumption control: `power_consumption_control_mode` (holding 124, 0–3) and
  `input_power_limit` (holding 125, kW) are numbers, disabled by default, for an automation
  that caps the pump on the capacity tariff or pushes surplus solar into it. 124 is a
  number, not a select: what 0–3 mean depends on the controller's power consumption
  control mode (SG-Ready or PL/LU), which an installer sets and Modbus can't read, so
  options can't be named honestly (library errata). The README warns about it. Still to verify on the
  reference pump: whether the limit covers the immersion heater, and whether it lapses
  when the BMS stops writing.
- The heat pump unit's power output and consumed power (input 157/158) come in kW and are
  shown in W (`suggested_unit_of_measurement`), like the electric meter and most power
  sensors such as a P1 meter: Home Assistant's history draws one graph per unit. Power
  measurements show in W; power settings (`input_power_limit`) keep the pump's unit, kW.
  An entity created before this keeps kW and, with display precision 0 in W, shows three
  decimals in kW; changing its unit to W in the entity settings fixes both.
- State classes: `measurement` for temperatures, power, gears and percentages;
  `total_increasing` for operating hours (device class `duration`) and the electric meter's
  kWh (device class `energy`).
- The electric meter is the current limiter's meter on the house connection, so it
  measures the whole house, not the heat pump. It reports its energy twice, and both are
  disabled by default: they duplicate the house's own meter (P1) and would read as the
  heat pump's consumption in the energy dashboard. `kwh_total` (input 83–84, 32-bit)
  practically never wraps, but its LSB-first word order comes from the community
  (CJNE #292), not from the protocol document, and the reference pump has no meter to
  confirm it; a wrong decode under `total_increasing` would pollute the long-term
  statistics for good. `meter_value` (input 81, 16-bit) wraps after 65535 kWh, which
  `total_increasing` reads as a reset. The phase powers are enabled: they show what the
  current limiter acts on.
- The energy statistics (library `energy_statistics`, input 348–397) are the display's
  energy and COP per circuit for the last 12 months and the 12 before. They have device
  class `energy` but no state class: both periods roll per month, so a value drops when a
  month falls out (python-thermia-genesis#33), and neither `total_increasing` nor `total`
  fits a rolling sum. All are disabled by default: no protocol edition lists them, they
  are verified on a Calibra 17.1 only, and a pump without them reads 0 kWh (the library
  reads a COP of 0 as no value).
- One derived `binary_sensor` "Alarm" (device class `problem`, enabled) on the main device is
  on when any alarm input is on, for notifications. The alarm inputs are the binary sensors
  with device class `problem` of the parts the pump has, so an absent part's alarms don't
  count; they are all discrete inputs, so the alarm is unavailable while those fail to
  refresh.
- Enabled by default: the heating climate, the measured temperatures of the heating
  circuit (brine and condenser in and out, discharge pipe, outdoor, room), operational
  mode (a select), running demand 1, compressor gear, speed, operating hours and whether
  it runs, heat output and power consumption, the immersion heater step and whether the
  external heater runs, the hot water top temperature, and the electric meter's phase
  powers. The refrigerant circuit (liquid line, suction gas, dew and bubble points,
  superheat, subcooling, pressures) is disabled by default. So are the heating system's
  supply and return line temperatures: a pump without system sensors reads them as unknown.
  A set point of an absent part (the buffer tank's) can read 0.0; it is disabled, so it
  stays out of sight. Everything else (queued demands, PID values, flags, settings,
  individual alarms) is disabled by default.
- Coils and holding registers (settings) and the alarm inputs have entity category
  `diagnostic`; a setting has no state class, so it stays out of the long-term statistics.
- Entity names come from translations (`has_entity_name`), in English and Dutch.

## Diagnostics

- The entry's diagnostics hold the raw registers and the decoded values per subsystem, like
  `thermia-genesis dump`, with the host and the entry's title redacted. They are the first thing to ask for in a
  report about another pump or firmware.
- They call the library's `dump` on the coordinator's unit, so they read the whole pump
  again (about 0.4 s) and their `dump` is exactly the JSON of `thermia-genesis dump`: a
  report becomes a test fixture as is. Beside it, the redacted config entry and the
  coordinator's state (last update, failing register spaces). A dropped link or a timeout
  replaces the dump with its error; the rest still comes.

## Coexistence

- The older `thermiagenesis` custom integration uses another domain, so both can be
  installed side by side, each with its own TCP connection. Two Modbus clients on the pump
  at once are untested, so the README says to disable the old one once the new one runs.
  Nothing is migrated from it.

## Tooling and process

- Tests use `pytest-homeassistant-custom-component`, `modbus_connection`'s mock unit and a
  copy of the library's Calibra 7 fixture; entity states are checked with syrupy snapshots.
  An end-to-end test goes through the real `async_get_unit` to an in-process `tmodbus`
  server. Tests never touch a real pump.
- The manifest's requirement on the library equals the dependency in `pyproject.toml`; a
  test keeps them in step, and Renovate bumps both in one pull request. The requirements of
  Home Assistant's `modbus` integration are development dependencies pinned to the versions
  of the tested Home Assistant release; Renovate leaves them alone, and a test compares
  them with the installed `modbus` manifest, so a new `pytest-homeassistant-custom-component`
  (a newer Home Assistant) fails until they follow, by hand on Renovate's branch.
- `translations/en.json` is `strings.json` with its references resolved, and the Dutch
  translation has exactly its keys; tests check both.
- uv (with a committed `uv.lock`; the project is not a package), ruff (`ALL` rules), mypy
  strict, prek. Strict TDD; CI enforces 100% line and branch coverage and runs hassfest and
  the HACS validation.
- Every change goes through a pull request with a Conventional Commits title. release-please
  turns merged commits into a release PR; merging it tags `vX.Y.Z` and creates the GitHub
  Release HACS installs from. It also bumps the version in `manifest.json`.
- The brand icon ships in `custom_components/thermia_genesis/brand/` (`icon.png` 256 px,
  `icon@2x.png` 512 px), which Home Assistant and HACS show for a custom integration. It is
  the Thermia logo that home-assistant/brands already holds for CJNE/thermiagenesis. The
  HACS validation checks it.
- A release candidate (`vX.Y.Z-rc.N`) is a tag an admin pushes on `main`; the release
  workflow turns it into a GitHub pre-release, which HACS offers to users who enabled beta
  versions. release-please doesn't see it, so the final notes still cover everything since
  the last stable release (PhoenixContactCharx learned this with 2.0.0). The rc's
  `manifest.json` keeps the last stable version, since only release-please bumps it.
- Development happens in the devcontainer, in a git worktree under `.worktrees/<branch>`.
