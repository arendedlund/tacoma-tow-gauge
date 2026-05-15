# Tacoma Tow Gauge

A custom in-vehicle temperature gauge for a Toyota Tacoma that displays ATF pan
temperature, torque converter outlet temperature, and engine coolant temperature
on a narrow bar display mounted inside a custom steering column clamshell.

## Purpose

Towing puts sustained thermal load on the transmission and drivetrain in ways that
the factory instrument cluster doesn't surface. This gauge adds real-time visibility
into the three temperatures that matter most during towing — letting the driver see
warning and critical states before damage occurs, not after.

## Goal

A permanently installed, key-on-activated display behind the steering wheel showing
three temperature channels with colour-coded warning and critical states. The device
must be self-contained (no OBD-II dongle visible), survive ignition-off power loss,
and leave the OBD-II port free for diagnostic tools.

## Display

**Microtips AWL-2801424T70N01** — 1424×280 px MIPI DSI bar display, 181.5×38.2mm
overall. The only reviewed option that fits inside the Tacoma instrument cluster
clamshell (38mm height limit). Likely uses ST7701S driver IC.

## Project Phases

### Phase 1 — CAN Reverse Engineering
Use a comma.ai panda + Cabana to capture live CAN traffic and confirm the arbitration
IDs, byte positions, and decoding formulas for all three temperature signals. Nothing
else can begin until PIDs are verified against the actual vehicle.

**Hardware**: comma.ai panda (already ordered), laptop

### Phase 2 — Proof-of-Concept Demo
Raspberry Pi CM5 drives the Microtips display via MIPI DSI. Panda connects via USB
as the CAN source. All three temperatures show live on the display in the vehicle,
with no permanent modifications made.

**Hardware**: CM5 + CM5 IO Board, Microtips display, MicroSD, panda (from Phase 1)

### Phase 3 — Direct CAN Integration
Remove the panda from the design. CM5 connects directly to the vehicle CAN bus at
a tap point that is not the OBD-II port, via an MCP2515 SPI CAN controller. OBD-II
port remains free.

**Hardware**: MCP2515 + TJA1050 SPI module, CAN tap connector (location TBD via Toyota TIS)

### Phase 4 — Permanent Installation
3D-printed steering column clamshell with display cutout. Power from the WSH
key-on accessory circuit via an automotive-grade 12V→5V DC-DC converter. Clean
wiring, no loose hardware, automatic power-on with the key.

**Hardware**: DC-DC converter, fuse tap, wiring materials, PETG filament

## Bill of Materials

See [bom.md](bom.md) for the full phase-by-phase BOM with part sources, cost
estimates, and purchase schedule.

**Total estimate**: ~$331–381 (excludes panda, already purchased)

## Architecture

```
src/
├── main.py              # Entry point; wires CAN reader and renderer together
├── can/
│   └── reader.py        # CAN bus thread; reads frames, dispatches to decoders
├── signals/
│   ├── loader.py        # Loads signal definitions from config/signals.json
│   └── decoder.py       # Decodes raw CAN frames → GaugeSignal values + state
├── display/
│   ├── renderer.py      # pygame render loop; targets /dev/fb0 or a desktop window
│   └── slot.py          # One DisplaySlot per signal; colour from thermal state
└── config/
    └── loader.py        # Loads signals.json and thresholds.json

config/
├── signals.json         # Arbitration IDs, PIDs, byte formulas per signal
└── thresholds.json      # Warning and critical thresholds per signal

assets/fonts/            # Bittypix Monospace OTF for display rendering
systemd/
└── gauge.service        # systemd unit for key-on autostart on CM5
```

New signals are added by editing `config/signals.json` — no code changes required.
Thresholds are in `config/thresholds.json` and are tunable without a rebuild.

## Development

### Requirements

- Python 3.11+
- `pip install -r requirements.txt`

### Run in windowed mode (macOS, no hardware)

```sh
python3 run.py --windowed --scale 0.5
```

This starts a desktop window at approximately the physical display size on a
2× Retina Mac. A CAN injector thread runs automatically, sweeping all three
temperature channels through normal → warning → critical and back on a 30-second
triangle-wave cycle so every display state is visible without any hardware.

### Run with a panda (Phase 2)

```sh
python3 run.py --bus-interface panda
```

### Run with SocketCAN / MCP2515 (Phase 3+)

```sh
python3 run.py --bus-interface socketcan
```

### Inject a fixed temperature manually (separate terminal)

```sh
python3 tools/inject_virtual_can.py --atf 145 --tc 155 --ect 108
```

## Development Methodology

This project uses [Spec Kit](https://github.com/speckit) — a specification-driven
workflow where each feature starts with a written spec, then a technical plan, then
a task breakdown, before any code is written. The specs live in `specs/` and are
the source of truth for requirements, architecture decisions, open questions, and
the phased delivery strategy.

The current active spec is at
[specs/001-can-panda-display/](specs/001-can-panda-display/).

## Open Questions

| # | Question | Blocks |
|---|---|---|
| OQ-1 | Is engine oil temp accessible via enhanced OBD on 3rd gen V6? | Slot 1 content |
| OQ-2 | Do PIDs 0x1627/0x1628 respond on this specific VIN? | Signal decoder |
| OQ-3 | Is there a CAN gateway isolating OBD-II from powertrain bus? | Phase 3 tap strategy |
| OQ-4 | Safest accessible CAN tap point near steering column? | Phase 3 wiring |
| OQ-5 | MIPI DCS init sequence for AWL-2801424T70N01 (ST7701S)? | Phase 2 display driver |

OQ-5 is the current blocker for Phase 2 display bring-up. Contact Microtips at
mtusainfo@microtipsusa.com asking for the ST7701S initialization sequence for the
AWL-2801424T70N01.
