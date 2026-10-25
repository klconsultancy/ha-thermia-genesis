# Thermia Genesis for Home Assistant

A Home Assistant integration for Thermia ground source heat pumps on the Genesis controller
platform (Calibra, Atlas, Diplomat, Mega), read over Modbus TCP. It is built on the
[`thermia-genesis`](https://github.com/klconsultancy/python-thermia-genesis) library and
Home Assistant's own Modbus connection.

> **Status:** under development. The first release will be read-only.

## Requirements

- Home Assistant 2026.10 or later
- A heat pump with Genesis firmware 17.1 and Modbus TCP enabled

## Installation

Not released yet. The first release will install through
[HACS](https://hacs.xyz/) as a custom repository.

## The older `thermiagenesis` integration

The community `thermiagenesis` integration uses another domain, so both can run side by side
while you switch over. Entities are not migrated: remove the old integration once the new
one runs.

## License

[MIT](LICENSE)
