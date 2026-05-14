# Data Model: CAN Bus Gauge Display

**Branch**: `001-can-panda-display` | **Date**: 2026-05-14

---

## Entities

### CANFrame

A raw message received from the vehicle CAN bus.

| Field | Type | Description |
|---|---|---|
| arbitration_id | int | 11-bit CAN arbitration ID (e.g., `0x7E9` — TCM response) |
| data | bytes[0..8] | Payload bytes; length determined by DLC |
| timestamp | float | Monotonic timestamp of receipt (seconds since boot) |

**Notes**:
- Frames arrive continuously from the bus; the gauge only decodes frames matching
  known arbitration IDs.
- In Phase 2, frames arrive via panda USB (panda library). In Phase 3+, via SocketCAN
  (MCP2515). The source is transparent to the decoder layer.

---

### GaugeSignal

A named, human-readable value derived from one or more CAN frames. There is one
GaugeSignal instance per channel (oil temp, pan temp, TC temp).

| Field | Type | Description |
|---|---|---|
| name | str | Human label shown on display (e.g., "Oil Temp") |
| unit | str | Display unit; always "°C" in v1 |
| value | float \| None | Most recent decoded value; None if no valid reading yet |
| state | SignalState | Current thermal state (see enum below) |
| last_updated | float \| None | Monotonic timestamp of last valid decode |
| threshold_warning | float | °C at which state transitions to WARNING |
| threshold_critical | float | °C at which state transitions to CRITICAL |
| staleness_timeout | float | Seconds without a valid frame before state → NO_SIGNAL |
| plausible_min | float | Lowest physically plausible reading (e.g., −40 °C) |
| plausible_max | float | Highest physically plausible reading (e.g., 200 °C) |

**SignalState enum**:

| Value | Meaning | Display behavior |
|---|---|---|
| `WAITING` | No frame received yet since power-on | Slot shows "—" |
| `NORMAL` | Value within normal operating range | Default color |
| `WARNING` | Value ≥ warning threshold | Warning color (amber) |
| `CRITICAL` | Value ≥ critical threshold | Critical color (red) |
| `NO_SIGNAL` | No valid frame within staleness_timeout | Slot shows "NO SIGNAL" |
| `FAULT` | Decoded value outside plausible range | Slot shows "FAULT" |

**State transition rules**:
```
on receive_frame(frame):
    decoded = decode(frame)
    if decoded < plausible_min or decoded > plausible_max:
        state = FAULT
    elif decoded >= threshold_critical:
        state = CRITICAL
    elif decoded >= threshold_warning:
        state = WARNING
    else:
        state = NORMAL
    value = decoded
    last_updated = now()

on tick():
    if last_updated is None:
        state = WAITING
    elif now() - last_updated > staleness_timeout:
        state = NO_SIGNAL
```

---

### SignalDecoder

Knows how to extract a GaugeSignal value from a CANFrame. One decoder per signal.

| Field | Type | Description |
|---|---|---|
| signal_name | str | Matches GaugeSignal.name |
| request_header | int | Arbitration ID to send the OBD-II request to (Phase 2 only) |
| response_header | int | Arbitration ID of the expected response frame |
| mode | int | OBD-II mode byte (e.g., 0x22) |
| pid | int | OBD-II PID (e.g., 0x1627) |
| decode_fn | callable | Function: bytes → float (applies scale/offset formula) |

**Known decoders** (confirmed for 3rd gen V6 Tacoma):

| Signal | response_header | pid | decode_fn |
|---|---|---|---|
| ATF Pan Temp | `0x7E9` | `0x1627` | `(A*459/255) + (B*1.6/255) - 40` then convert F→C |
| TC Outlet Temp | `0x7E9` | `0x1628` | Same formula |
| Engine Oil Temp | TBD | TBD | TBD (see OQ-1 in research.md) |

---

### DisplaySlot

A fixed region of the 280×1424 px screen assigned to one GaugeSignal.

| Field | Type | Description |
|---|---|---|
| signal_name | str | Which GaugeSignal this slot renders |
| position | Rect | Pixel bounding box on the 280×1424 canvas |
| label | str | Static label text (e.g., "OIL TEMP") |
| current_value | float \| None | Mirrored from GaugeSignal.value for rendering |
| current_state | SignalState | Mirrored from GaugeSignal.state |

**Color mapping** (implementation detail, configurable):

| State | Color intent |
|---|---|
| NORMAL | Default (white or neutral) |
| WARNING | Amber |
| CRITICAL | Red |
| NO_SIGNAL / FAULT / WAITING | Dim gray or muted |

---

### ThresholdConfig

Persisted configuration for per-signal thresholds. Loaded at startup from
`config/thresholds.json`; editable without firmware rebuild.

| Field | Type | Description |
|---|---|---|
| signal_name | str | Identifies which GaugeSignal this applies to |
| warning_celsius | float | Warning threshold in °C |
| critical_celsius | float | Critical threshold in °C |
| staleness_timeout_s | float | No-signal timeout in seconds |

**Default values** (from research.md §5):

```json
[
  {
    "signal_name": "Oil Temp",
    "warning_celsius": 135.0,
    "critical_celsius": 150.0,
    "staleness_timeout_s": 10.0
  },
  {
    "signal_name": "ATF Pan Temp",
    "warning_celsius": 130.0,
    "critical_celsius": 150.0,
    "staleness_timeout_s": 10.0
  },
  {
    "signal_name": "TC Outlet Temp",
    "warning_celsius": 140.0,
    "critical_celsius": 160.0,
    "staleness_timeout_s": 10.0
  }
]
```

---

## Relationships

```
ThresholdConfig ──► GaugeSignal (1:1, loaded at startup)
SignalDecoder   ──► GaugeSignal (1:1, produces values)
CANFrame        ──► SignalDecoder (many:1, filtered by response_header + pid)
GaugeSignal     ──► DisplaySlot (1:1, slot mirrors signal state)
```

---

## Display Layout

The display is mounted in **landscape orientation** — wide and short, spanning
horizontally behind the steering wheel. Physical constraints from the steering column
clamshell: max ~38mm tall (1.5"), max ~279mm wide (11").

The Microtips AWL-2801424T70N01 in landscape:
- Rendered resolution: **1424 × 280 px** (width × height)
- Active area: **170.9mm wide × 33.6mm tall** (6.7" × 1.3") — fits within both limits
- Overall outline: 181.5mm × 38.2mm

Three gauge slots divide the 1424px width equally:

```
x=0          x=474       x=948        x=1424
┌────────────┬────────────┬────────────┐  y=0
│            │            │            │
│  OIL TEMP  │  ATF PAN   │ TC OUTLET  │  280 px tall
│  XXX °C    │  XXX °C    │  XXX °C    │
│            │            │            │
└────────────┴────────────┴────────────┘  y=280
  ~474 px      ~474 px      ~476 px
```

Each slot is approximately 474×280 px — nearly square, readable at a glance.

**Note**: If engine oil temperature is confirmed inaccessible (OQ-1), the oil slot will
display an alternative signal (e.g., coolant temp) or be reconfigured. Slot geometry
and width divisions do not change regardless of signal assignment.
