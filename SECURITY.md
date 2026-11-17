# Security policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Report vulnerabilities privately through [GitHub's private vulnerability reporting](https://github.com/klconsultancy/ha-thermia-genesis/security/advisories/new), not in a public issue.

Include what an attacker can do, the steps to reproduce it, and the affected version or commit. You will get an answer within a week. Once a fix is released, the advisory is published with credit to you unless you prefer otherwise.

The integration talks Modbus to a Thermia heat pump, which has no authentication of its own, through Home Assistant's modbus integration and the thermia-genesis library. It only reads today, but the pump accepts writes to its settings. Issues that let the integration write to the pump without the user asking, leak the pump's address (diagnostics redact it), or make it misreport the pump's state (an alarm, a temperature) are treated as the most severe. Register decoding belongs to the library: report it there unless it only shows in Home Assistant.
