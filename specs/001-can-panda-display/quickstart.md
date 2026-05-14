# Quickstart: CAN Bus Gauge Display

**Branch**: `001-can-panda-display` | **Date**: 2026-05-14

This guide gets Phase 2 (demo bench rig) running: CM4 + panda USB → live temperature
display. Phase 3+ (direct CAN tap) replaces the panda with MCP2515; the application
code is unchanged.

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
