# Contract: CAN Signal Definition Format

**Version**: 1.0 | **Date**: 2026-05-14

---

## Purpose

Defines the format for declaring a new gauge signal. Any new signal (Phase 3+
extensions) MUST conform to this contract. The gauge loop loads all signals from
`config/signals.json` at startup; no code changes are required to add a signal.

---

## Signal Definition Schema

```json
{
  "name": "<string>",
  "label": "<string>",
  "unit": "<string>",
  "request_header": "<hex string>",
  "response_header": "<hex string>",
  "obd_mode": "<hex string>",
  "obd_pid": "<hex string>",
  "decode": {
    "formula": "<string>",
    "variables": {
      "<var>": { "byte_index": <int>, "byte_count": <int> }
    }
  },
  "plausible_min": <float>,
  "plausible_max": <float>,
  "warning_threshold": <float>,
  "critical_threshold": <float>,
  "staleness_timeout_s": <float>
}
```

### Field Descriptions

| Field | Required | Description |
|---|---|---|
| `name` | ✅ | Unique machine identifier (e.g., `"atf_pan_temp"`) |
| `label` | ✅ | Human label for display slot (e.g., `"ATF PAN"`) |
| `unit` | ✅ | Display unit string (e.g., `"°C"`) |
| `request_header` | ✅ | Hex arbitration ID to send OBD-II request (e.g., `"0x7E1"`) |
| `response_header` | ✅ | Hex arbitration ID of expected response (e.g., `"0x7E9"`) |
| `obd_mode` | ✅ | OBD mode byte in hex (e.g., `"0x22"` for enhanced) |
| `obd_pid` | ✅ | OBD PID in hex (e.g., `"0x1627"`) |
| `decode.formula` | ✅ | Python expression using variable names from `decode.variables` |
| `decode.variables` | ✅ | Map of variable name → byte position in response payload |
| `plausible_min` | ✅ | Minimum physically valid value; readings below → FAULT |
| `plausible_max` | ✅ | Maximum physically valid value; readings above → FAULT |
| `warning_threshold` | ✅ | Value at which display color changes to warning |
| `critical_threshold` | ✅ | Value at which display color changes to critical |
| `staleness_timeout_s` | ✅ | Seconds without update before state → NO_SIGNAL |

---

## Example: ATF Pan Temperature

```json
{
  "name": "atf_pan_temp",
  "label": "ATF PAN",
  "unit": "°C",
  "request_header": "0x7E1",
  "response_header": "0x7E9",
  "obd_mode": "0x22",
  "obd_pid": "0x1627",
  "decode": {
    "formula": "((A * 459/255) + (B * 1.6/255) - 40 - 32) * 5/9",
    "variables": {
      "A": { "byte_index": 3, "byte_count": 1 },
      "B": { "byte_index": 4, "byte_count": 1 }
    }
  },
  "plausible_min": -40.0,
  "plausible_max": 200.0,
  "warning_threshold": 130.0,
  "critical_threshold": 150.0,
  "staleness_timeout_s": 10.0
}
```

---

## Adding a New Signal

1. Capture the signal with Cabana; confirm arbitration ID, byte positions, and formula.
2. Add a new entry to `config/signals.json` conforming to this schema.
3. Add a new entry to `config/thresholds.json` if different from defaults.
4. Restart the gauge service — no code changes required.

This satisfies FR-012 (extensibility without modifying existing code) and constitution
Principle II (Sensor Modularity).
