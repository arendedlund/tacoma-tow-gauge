# Contract: Display Slot Layout

**Version**: 1.0 | **Date**: 2026-05-14

---

## Physical Display

- **Panel**: Microtips AWL-2801424T70N01
- **Native resolution**: 280 × 1424 px
- **Mounted orientation**: **Landscape** — the long axis runs horizontally
- **Rendered resolution**: 1424 × 280 px (width × height)
- **Active area (landscape)**: 170.9mm wide × 33.6mm tall (6.7" × 1.3")
- **Interface**: MIPI DSI (2-lane on CM5)
- **Clamshell constraints**: max 279mm (11") wide; max 38mm (1.5") tall — panel satisfies both

---

## Slot Layout Contract

The display is divided into N equal **vertical bands** (columns), one per active signal.
The display spans horizontally behind the steering wheel; slots are read left-to-right.
Each slot MUST render independently; a fault or state change in one slot MUST NOT affect
others.

### Slot Structure

Each slot is approximately square (~474×280 px):

```
┌─────────────────────────┐
│  LABEL       (top)      │  Signal label (e.g., "OIL TEMP")
│                         │
│  VALUE UNIT  (center)   │  Numeric value + unit (e.g., "112 °C")
│          or FAULT MSG   │  "NO SIGNAL" / "FAULT" / "—"
│                         │
│  [state color fills]    │  Background or text color encodes state
└─────────────────────────┘
```

### State-to-Color Mapping

| SignalState | Visual treatment |
|---|---|
| NORMAL | Neutral background; value text in default color |
| WARNING | Amber accent (background tint or value text color) |
| CRITICAL | Red accent (background tint or value text color) |
| WAITING | Dim; value shows "—" |
| NO_SIGNAL | Dim; value shows "NO SIGNAL" in muted text |
| FAULT | Dim; value shows "FAULT" in muted text |

**Requirement**: The three thermal states (NORMAL, WARNING, CRITICAL) MUST be
distinguishable without reading the numeric value, from the driver's seated position.
This satisfies SC-008.

### Default 3-Signal Layout (1424 × 280 px landscape)

```
Slot 1: x=0     width=474  → "OIL TEMP" (or contingency signal)
Slot 2: x=475   width=474  → "ATF PAN"
Slot 3: x=950   width=476  → "TC OUTLET"
```

**Contingency**: If engine oil temperature is confirmed inaccessible (OQ-1), Slot 1
will be reassigned to coolant temperature or another confirmed signal. Slot geometry
does not change — only the signal binding.

---

## Rendering Contract

The rendering loop MUST:
1. Run at a fixed target frame rate (minimum 10 fps; 30 fps preferred).
2. Re-read all GaugeSignal states each frame; never cache state across frames.
3. Update slot color atomically with the value text in the same draw call.
4. Never block the render loop on CAN I/O; signal decoding runs in a separate thread.

The CAN reader thread MUST:
1. Write decoded values and states to GaugeSignal objects under a lock.
2. Not interact with display output directly.
