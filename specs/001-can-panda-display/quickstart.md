# Quickstart: CAN Bus Gauge Display

**Branch**: `001-can-panda-display` | **Date**: 2026-05-14

This guide gets Phase 2 (demo bench rig) running: CM5 + panda USB → live temperature
display. Phase 3+ (direct CAN tap) replaces the panda with MCP2515; the application
code is unchanged.

---

## Local Development (No Hardware)

Develop and test the signal decoder, state machine, and display rendering on macOS
before any hardware arrives. No panda, CM5, or MIPI display required.

### Virtual CAN Bus

`python-can` ships a built-in `virtual` interface: an in-memory channel that lets
multiple processes exchange CAN frames on the same machine.

```bash
pip install python-can cantools
```

**Inject synthetic frames** (save as `tools/inject_virtual_can.py`):

```python
import can, time

bus = can.interface.Bus(channel='test', interface='virtual')

while True:
    # Simulate a Mode 22 response for PID 0x1627 (ATF pan temp ≈ 95 °C / 203 °F)
    # Formula: (A*459/255) + (B*1.6/255) - 40 °F → °C; A=120, B=0 gives ~95 °C
    data = bytes([0x05, 0x62, 0x16, 0x27, 120, 0, 0, 0])
    bus.send(can.Message(arbitration_id=0x7E9, data=data, is_extended_id=False))
    time.sleep(1)
```

In the gauge app, open the same channel:

```python
bus = can.interface.Bus(channel='test', interface='virtual')
```

Both processes share the channel by name — the injector drives the reader.

### pygame Windowed Mode (macOS)

The display renderer runs in a desktop window instead of writing to `/dev/fb0`.
Detect the absence of framebuffer hardware and call
`pygame.display.set_mode((1424, 280))` instead of initializing the framebuffer driver.
Pass `--windowed` to opt in explicitly:

```bash
python3 src/main.py --config config/ --windowed
```

This renders the full 1424×280 landscape layout in a macOS window — no MIPI hardware
needed to validate slot layout, color states, or font sizing.

### Toyota DBC Signal Exploration

The Toyota 2017 reference powertrain DBC is at
`~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc`.

Key signals already identified (see `research.md §2a` for full detail):

| Frame | ID | Signal | Formula | Likely meaning |
|---|---|---|---|---|
| ECT1S92 | 0x3BC | BV_THOCL | `raw × 0.625 − 50` °C | ATF temperature (broadcast candidate) |
| ENG1S23 | 0x3C1 | GATHW | `signed_raw × 0.625` °C | Engine coolant temperature |
| ECT1S92 | 0x3BC | B_OILW | 1-bit flag | Transmission oil warning |
| ECT1S92 | 0x3BC | B_GEAR | 4-bit | Current gear |

Load and inspect the DBC with cantools:

```python
import cantools

db = cantools.database.load_file(
    '/Users/<you>/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc'
)

# Inspect the ATF temp frame
msg = db.get_message_by_name('ECT1S92')
for s in msg.signals:
    print(f"  {s.name}: bits={s.start}|{s.length} scale={s.scale} offset={s.offset}")

# Simulate decoding a raw captured frame
# BV_THOCL raw=240 → 240*0.625-50 = 100 °C (normal ATF operating temp)
decoded = msg.decode(bytes([0x00, 0x00, 0x00, 0xF0, 0x00, 0x00, 0x00, 0x00]))
print(decoded)
```

Note: Mode 22 PIDs (0x1627 ATF pan, 0x1628 TC outlet) are request/response pairs and
are **not** in the DBC — they must be verified with the panda in Phase 1. The DBC
only covers continuously broadcast frames.

---

## Hardware Required (Phase 2 Demo)

- Raspberry Pi Compute Module 5 + CM5 IO Board
- Microtips AWL-2801424T70N01 display + MIPI ribbon cable
- comma.ai panda (OBD-II dongle form factor)
- OBD-II cable to connect panda to vehicle (or CAN bus bench setup)
- 12V→5V automotive DC-DC converter (to power CM4 from vehicle or bench supply)

---

## 1. Flash Raspberry Pi OS Lite (64-bit)

```bash
# Use Raspberry Pi Imager; select "Raspberry Pi OS Lite (64-bit)"
# Enable SSH, set hostname: tacoma-gauge
# Set locale and timezone
```

---

## 2. Install Dependencies

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git libsdl2-dev

python3 -m venv /opt/gauge-env
source /opt/gauge-env/bin/activate

pip install python-can pygame pillow
pip install git+https://github.com/commaai/panda.git
```

---

## 3. Configure CAN Interface (Phase 2 — panda USB)

The panda appears as a USB device. The `panda` Python library handles enumeration:

```python
from panda import Panda
p = Panda()
p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)  # passive sniff mode
```

No SocketCAN configuration needed for Phase 2.

*Phase 3 swap*: Replace with MCP2515 SPI setup:
```bash
# Add to /boot/config.txt:
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
# Then:
sudo ip link set can0 up type can bitrate 500000
```
And replace `Panda()` with `can.interface.Bus('can0', interface='socketcan')`.

---

## 4. Configure the Display

Add the Microtips panel Device Tree overlay to `/boot/config.txt`:

```
# MIPI DSI panel (custom overlay — see display bring-up notes)
dtoverlay=tacoma-gauge-panel
display_auto_detect=0
```

The panel overlay requires the DCS initialization sequence from Microtips. Request
`AWL-2801424T70N01` init commands from Microtips support before this step.

---

## 5. Load Signal and Threshold Config

```bash
mkdir -p /opt/gauge/config
cp config/signals.json /opt/gauge/config/
cp config/thresholds.json /opt/gauge/config/
```

Edit `/opt/gauge/config/thresholds.json` to adjust warning/critical values without
reflashing (see `contracts/signal-contract.md` for format).

---

## 6. Run the Gauge

```bash
source /opt/gauge-env/bin/activate
python3 src/main.py --config /opt/gauge/config
```

Expected startup sequence:
1. Config loads → signals and thresholds initialized
2. CAN interface connects (panda USB enumerated or SocketCAN up)
3. Display initializes → slots show "—" (WAITING state)
4. First valid CAN frames received → slots update with decoded values
5. All three temperature slots showing live data within SC-001/002/003 criteria

---

## 7. Validate Phase 1 Signal Discovery

During Phase 1 (Cabana capture), use this command to query a specific PID via panda:

```python
from panda import Panda
p = Panda()
# Send Mode 22 request for ATF pan temp (PID 0x1627) to TCM (0x7E1)
p.can_send(0x7E1, bytes([0x03, 0x22, 0x16, 0x27, 0x00, 0x00, 0x00, 0x00]), 0)
# Read responses and look for 0x7E9 frames
msgs = p.can_recv()
for msg in msgs:
    if msg[3] == 0x7E9:
        print(f"TCM response: {msg[1].hex()}")
```

Cross-reference with Cabana captures to confirm byte positions.

---

## Key Files

| File | Purpose |
|---|---|
| `src/main.py` | Entry point; initializes all subsystems |
| `src/can/reader.py` | CAN bus thread; reads frames, calls decoders |
| `src/signals/decoder.py` | Decodes raw CAN frames into GaugeSignal values |
| `src/display/renderer.py` | Renders DisplaySlots to framebuffer |
| `config/signals.json` | Signal definitions (see `contracts/signal-contract.md`) |
| `config/thresholds.json` | Warning/critical thresholds per signal |
