# Thermia Genesis for Home Assistant

A Home Assistant integration for Thermia ground source heat pumps on the Genesis controller
platform (Calibra, Atlas, Diplomat, Mega), read over Modbus TCP. It is built on the
[`thermia-genesis`](https://github.com/klconsultancy/python-thermia-genesis) library and
Home Assistant's own Modbus connection.

> **Status:** the first releases are read-only: the integration shows what the pump reports
> and never writes to it. Changing settings comes later.

## Requirements

- Home Assistant 2026.10 or later
- A heat pump with Genesis firmware 17.1 and Modbus TCP enabled

## Installation

The integration installs through [HACS](https://hacs.xyz/) as a custom repository:

1. In HACS, open the menu (⋮) → **Custom repositories**.
2. Add `https://github.com/klconsultancy/ha-thermia-genesis` with the type **Integration**.
3. Search for **Thermia Genesis**, download it and restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & services → Add integration** and pick **Thermia Genesis**.
2. Enter the heat pump's IP address or host name, and the Modbus TCP port (usually 502).

The integration reads the firmware to check the connection. It connects through Home
Assistant's own Modbus integration, so it shares one connection with Home Assistant's
`modbus` integration, or with another integration built on it, that talks to the same
address. If that one uses other connection settings for the address, setup stops with an
error saying the address is in use. To change the address later, use **Reconfigure** on the
entry: its entities and their history are kept.

## What you get

- A **Thermia Genesis** device with the pump's status (operational mode, running demand)
  and an **Alarm** binary sensor that is on while any alarm input is on, which is the one
  to notify on.
- One device per part the pump has (heat pump unit, heating, mix valve 1, hot water, hot gas
  heat recovery, cooling, pool, electric meter, energy statistics). An optional part the
  pump doesn't have (mix valve 1, hot gas heat recovery, pool, electric meter) gets no
  device.
- An entity for every value the library reads. A curated set is enabled, mainly the
  temperatures, the compressor, the heaters and the operational mode. The rest (settings,
  individual alarms, the refrigerant circuit, the energy statistics) is disabled; enable
  what you need.
- A **Heating** climate: the room temperature, the comfort wheel as the target, and
  heating on or off.
- A **Hot water** water heater: the water temperature, the stop temperature as the
  target, and hot water on or off. The start temperature is a number next to it, and must
  stay below the stop: to raise both, set the stop first; to lower both, the start first.
- A **Reset alarms** button on the main device.
- The **Operational mode** (off, standby, on auto) as a select on the main device.
- **Power consumption control** (disabled by default): the control mode (0–3) and the
  input power limit (kW) of the heat pump unit, for an automation that limits the pump's
  power. **Read this before you enable them.** What the mode values mean depends on the
  controller's power consumption control mode, which an installer sets and which can't be
  read over Modbus:
  - SG-Ready: 0 Normal, 1 Load-Up, 2 EVU (blocks the compressor), 3 Boost;
  - PL/LU: 0 Normal, 1 and 3 Power Limit (the input power limit applies), 2 Load-Up.

  So 0 undoes either, but 1 caps power in one mode and asks for more heat in the other.
  On a pump without a configured mode the values probably do nothing. The **Smart grid
  mode** sensor (disabled by default) shows the active SG-Ready mode; it may not reflect a
  PL/LU limit. A limit set too low stops the compressor. Not yet tested: whether the limit
  covers the immersion heater, and whether it lapses when nothing writes it any more.
  Write only when the value changes: whether the pump stores these registers in memory
  that wears out is unknown.
- The other settings show as diagnostic sensors until they can be written.
- Entity names in English and Dutch.

The pump is read every 30 seconds. When a register space fails to read, only its entities
become unavailable, and the integration keeps polling without reloading.

## Reporting a problem

Download the diagnostics of the entry (**Settings → Devices & services → Thermia Genesis →
⋮ → Download diagnostics**) and attach them to an issue. They hold every register the pump has, raw and decoded, with the host and the entry's
title redacted: the same JSON as `thermia-genesis dump`. A wrong or missing value, or an
unsupported firmware, belongs in the
[library's issues](https://github.com/klconsultancy/python-thermia-genesis/issues). Report
security issues privately as described in [SECURITY.md](SECURITY.md).

## The older `thermiagenesis` integration

The community `thermiagenesis` integration uses another domain, so both can be installed side
by side while you switch over. Each opens its own connection to the pump, though, and two
Modbus clients at once have not been tested against the pump: disable the old integration
once the new one runs. Entities are not migrated.

## Disclaimer

Not affiliated with Thermia AB. Controlling a heat pump remotely is at your own risk.

## License

[MIT](LICENSE)
