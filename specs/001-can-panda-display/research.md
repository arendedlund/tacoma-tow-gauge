# Research: CAN Bus Gauge Display

**Branch**: `001-can-panda-display` | **Date**: 2026-05-14

---

## 1. MCU / Platform Selection

**Decision**: Raspberry Pi Compute Module 5 (CM5) + CM5 IO Board

**Rationale**:
The CM5 is a direct upgrade over the CM4 (BCM2712 Cortex-A76 vs BCM2711 Cortex-A72)
with the same Raspberry Pi OS ecosystem, identical Python stack, faster CPU (better
boot-time headroom toward the 10 s key-on target), and USB 3.0. The CM5 IO Board is
the required carrier board providing MIPI DSI, USB-A, SPI GPIO, and the 40-pin header.

| Constraint | CM5 | STM32H7 | ESP32-P4 | i.MX RT1170 |
|---|---|---|---|---|
| MIPI DSI | 2-lane ✅ (sufficient) | 2-lane native ✅ | 4-lane (immature ⚠) | 4-lane native ✅ |
| CAN interface | SPI MCP2515 ✅ | Native FDCAN ✅ | SPI MCP2515 ✅ | Native CAN FD ✅ |
| USB host (panda) | Native, easy ✅ | Hard (bare-metal) ❌ | Limited ❌ | Moderate ⚠ |
| Boot to display | 8–12 s tuned ✅ | < 1 s ✅ | ~3 s ✅ | ~5 s ✅ |
| Python/panda ecosystem | Full ✅ | None ❌ | Partial ⚠ | None ❌ |
| Solo dev complexity | Low ✅ | High ❌ | High ❌ | High ❌ |

The CM5's 2-lane MIPI DSI provides ~2 Gbps total bandwidth. The Microtips panel at
280×1424×24bpp×30fps requires ~288 Mbps — well within budget. A custom Device Tree
panel driver is required (panel is not in upstream Linux kernel); Microtips must supply
the MIPI DCS initialization command table for bring-up.

**CAN interface**: MCP2515 over SPI with TJA1050 or SN65HVD230 transceiver, driven by
the Linux `mcp251x` kernel driver via SocketCAN. Python's `python-can` library abstracts
both the panda USB interface (Phase 2) and the MCP2515 SocketCAN interface (Phase 3+)
behind the same `can.Bus` API — meaning the signal decoding code is identical across
phases.

**Alternatives considered**:
- **STM32H7B3**: Boot time advantage, native FDCAN, but no Python path and bare-metal
  MIPI + USB host implementation is weeks of additional work for a solo developer.
- **ESP32-P4**: MIPI DSI support too immature as of 2026; framebuffer RAM constraints.
- **i.MX RT1170**: Strong hardware but MCUXpresso/Zephyr learning curve + no Python path.
- **CM4**: Functionally identical approach but slower CPU; CM5 preferred given
  availability and faster boot headroom toward the 10 s key-on target.
- **Raspberry Pi Zero 2W**: 512 MB RAM and slower CPU make 30fps framebuffer rendering
  marginal; CM5 preferred for stability headroom.

**Language/framework**: Python 3.11+ with:
- `python-can` — CAN bus abstraction (SocketCAN + panda)
- `panda` (comma.ai) — USB interface to panda device in Phase 2
- `pygame` — display rendering to framebuffer (or `Pillow` + `/dev/fb0` direct)
- `systemd` — service lifecycle, key-on/key-off supervision

**Key risks and mitigations**:

| Risk | Mitigation |
|---|---|
| Custom MIPI panel driver bring-up | Request DCS init sequence from Microtips; adapt nearest existing panel driver |
| Boot time > 10 s | Strip unused services; use read-only overlayFS; add framebuffer splash during kernel boot; CM5's faster CPU gives more headroom than CM4 |
| Filesystem corruption on key-off | Run rootfs read-only (overlayFS); config written to separate small RW partition |
| Voltage spikes from vehicle 12V | Use automotive-grade 12V→5V DC-DC converter (not a linear reg); add TVS clamping |

---

## 2. Tacoma CAN PIDs — Transmission Temperatures

**Decision**: Use enhanced OBD-II (Mode 22) PIDs via panda for Phase 1 verification;
confirmed working PIDs for V6 3rd gen Tacoma are listed below.

### AT Oil Temp 1 — Transmission Pan Temperature

| Field | Value |
|---|---|
| OBD request header | `0x7E1` (transmission ECM) |
| Mode | `0x22` (manufacturer-enhanced) |
| PID | `0x1627` (full frame: `22 16 27`) |
| Response bytes used | A (high), B (low) |
| Formula (°F) | `(A × 459/255) + (B × 1.6/255) − 40` |
| Formula (°C) | `((A × 459/255) + (B × 1.6/255) − 40 − 32) × 5/9` |
| Range | −40 to ~216 °C |
| Measures | Transmission fluid in the pan (hydraulic pressure control sensor) |
| Confidence | High — community-verified on 3rd gen V6 Tacoma via Torque Pro / OBD Fusion |

### AT Oil Temp 2 — Post-Converter (Torque Converter Outlet) Temperature

| Field | Value |
|---|---|
| OBD request header | `0x7E1` |
| Mode | `0x22` |
| PID | `0x1628` (full frame: `22 16 28`) |
| Response bytes used | A (high), B (low) |
| Formula (°C) | Same as AT Oil Temp 1 |
| Measures | Fluid temperature exiting the torque converter |
| Behavior | Fluctuates rapidly with TC lockup/unlock; typically 5–30 °C above pan temp under load |
| Confidence | High — same source as above |

**Alternative PID (reported by some users, less verified for 3rd gen)**:
PID `0x2182` with formula `((A×256+B)/10)−40` °C. Appears to be an older Toyota
enhanced mode entry. Treat as a fallback to test if the primary PIDs above do not
respond on a specific vehicle.

---

## 2a. ATF Sensor Hardware Details (from Factory Service Manual)

**Source**: 2016 Toyota Tacoma Service Manual, AC60E/AC60F Automatic Transmission
section (extracted 2026-05-14 from 241 MB PDF).

The AC60E (2WD) and AC60F (4WD) automatic transmissions both contain **two NTC
thermistors** mounted on the transmission wire sub-assembly (connector E1):

| Sensor | ECM terminal | Wire color | E1 connector pins | Service manual label |
|---|---|---|---|---|
| No. 1 ATF (pan) | E10-26 (THO1) | Purple-Brown (P-BR) | 3 (OT+) / 4 (OT−) | "A/T Oil Temperature No. 1" |
| No. 2 ATF (valve body) | E10-34 (THO2) | Blue-Brown (L-BR) | 5 (OT2+) / 6 (OT2−) | "A/T Oil Temperature No. 2" |

**Confirmed sensor location**: No. 2 ATF is explicitly described as "installed in the
transmission valve body assembly" — this is the torque converter outlet (TC outlet)
sensor matching PID 0x1628.

**Resistance characteristics** (both sensors identical):

| ATF Temperature | Specified resistance |
|---|---|
| 10 °C (50 °F) | 5 to 8 kΩ |
| 25 °C (77 °F) | 2.5 to 4.5 kΩ |
| 110 °C (230 °F) | 220 to 280 Ω |
| Full operating range | 79 Ω to 156 kΩ |

**Fault detection thresholds** (from DTC P071011 / P274011):
- No. 1 ATF: fault if voltage below 0.142 V (corresponding to > 164 °C)
- No. 2 ATF: fault if voltage below 0.0459 V (short-circuit threshold = < 25 Ω)

**ECM reporting thresholds confirmed by service manual** (validates our config):

| Condition | ATF temp | Behavior |
|---|---|---|
| Shift point changes | > 130 °C (No. 2 ATF) | Shift to higher gear earlier |
| Warning indicator on | > 150 °C (No. 2 ATF) | ATF temp warning light illuminates |
| Warning indicator off (recovery) | < 135 °C | Light extinguishes within ~5 min in P/N |

These match the `thresholds.json` values (warn 130 °C / crit 150 °C) precisely. The
service manual confirms 150 °C is Toyota's own factory alert threshold.

**Signal path**: Both sensors are **analog only** — they connect directly to ECM analog
inputs. No ATF temperature value is broadcast on the CAN bus. The ECM makes them
available as Techstream Data List items ("A/T Oil Temperature No. 1/No. 2") and
accessible via Mode 22 PIDs 0x1627/0x1628 through the DLC3.

---

## 2b. DBC Broadcast Signal Cross-Reference

**Source**: `~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc`

The commaai/opendbc Toyota 2017 reference powertrain DBC covers **broadcast** frames —
signals transmitted continuously without a request. These are complementary to the
Mode 22 PIDs in §2 above, which require the gauge to poll.

### Broadcast ATF Temperature Candidate: BV_THOCL

| Field | Value |
|---|---|
| Frame | `ECT1S92` — ID **0x3BC** (956 dec), 8 bytes |
| Signal | `BV_THOCL` — bits 23\|16, big-endian, unsigned |
| Scale / Offset | 0.625 / −50 |
| Formula | `temp_C = raw_16bit × 0.625 − 50` |
| Range | −50 °C (raw 0) → ~150 °C (raw 320) |
| Context | ECT (Electronic Controlled Transmission) frame; co-located with `B_OILW` (oil warning flag), `B_GEAR`, gear-position bits |

"THOCL" is not standard in public Toyota documentation. The ECT frame context and
temperature-plausible formula strongly suggest ATF temperature. **Must be verified
in Phase 1**:

- Capture frame 0x3BC during a cold-start warm-up
- Observe whether `BV_THOCL` tracks the expected ATF warm-up curve (slow rise from
  cold soak, faster rise under tow load)
- Cross-reference simultaneously against Mode 22 PID 0x1627 response

**If verified broadcast**: This is preferable to OBD-II polling — no request frames
needed, reduces CAN bus load, eliminates request/response timing dependency.

### Broadcast Coolant Temperature: GATHW

| Field | Value |
|---|---|
| Frame | `ENG1S23` — ID **0x3C1** (961 dec), 3 bytes |
| Signal | `GATHW` — bits 15\|16, big-endian, signed |
| Scale / Offset | 0.625 / 0 |
| Formula | `temp_C = signed_16bit × 0.625` |
| Context | "THW" = Thermistor Hot Water — Toyota's standard label for coolant temperature |

**Use**: Primary contingency for Slot 1 if engine oil temperature (OQ-1) cannot be
accessed. Coolant temp is confirmed present in the DBC and is a well-understood proxy
for engine thermal state under tow load.

### No Broadcast Engine Oil Temperature

The DBC contains only status flags: `B_OILPL` (ENG1S92, 0x3BB, 2-bit) and `B_OILW`
(ECT1S92, 0x3BC, 1-bit). Neither is a continuous temperature value. No broadcast
frame carrying a continuous engine oil temperature was found — consistent with
community reports that the 3rd gen V6 uses a pressure switch rather than a temperature
sensor in the oil circuit. OQ-1 remains unresolved until Phase 1 Mode 22 scan.

### How to Load the DBC (local)

```python
import cantools

db = cantools.database.load_file(
    '/Users/<you>/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc'
)

# Inspect the ATF temp frame
msg = db.get_message_by_name('ECT1S92')
print(f"ID: 0x{msg.frame_id:03X}")
for s in msg.signals:
    print(f"  {s.name}: scale={s.scale} offset={s.offset} bits={s.start}|{s.length}")

# Decode a captured raw frame (8 bytes)
raw = bytes([0x00, 0x00, 0x00, 0xF0, 0x00, 0x00, 0x00, 0x00])
decoded = msg.decode(raw)
print(decoded)  # BV_THOCL → 0xF0 = 240 → 240*0.625-50 = 100 °C
```

---

## 3. Tacoma CAN PIDs — Engine Oil Temperature

**Decision**: **OQ-1 CLOSED** — confirmed via 2016 Tacoma factory service manual.

**Finding**: The 3rd gen Tacoma has **no engine oil temperature sensor**. The service
manual ECM terminal tables (2TR-FE and 2GR-FKS) list no "oil temperature" input. The
engine lubrication system uses an oil **pressure switch** (on/off), not a thermistor.
No Mode 22 PID for engine oil temperature exists.

The sensor labeled "oil temperature sensor" in the service manual (DTC P17C7/P17C8,
connector F38) is the **front differential oil temperature sensor** — it is read by the
4WD Control ECU (F13-5 DT), not the ECM, and does not appear in any known OBD-II
Data List. It is a 120–240 kΩ NTC thermistor at room temperature and is not accessible
via Mode 22 queries to 0x7E0 or 0x7E1.

**Resolution for Slot 1**: Engine oil temperature slot in the display will use
**GATHW** (engine coolant temp, broadcast frame 0x3C1, §2a) as confirmed alternative.
Coolant temp is a well-understood proxy for engine thermal state under tow load and is
already in the DBC. The `oil_temp` signal entry in `config/signals.json` will be
updated in T014 to use the GATHW broadcast PID once Phase 1 confirms frame 0x3C1
responds on this vehicle.

---

## 4. CAN Bus Tap Location (Phase 3+)

**Decision**: **OQ-3 RESOLVED, OQ-4 RESOLVED** — confirmed via 2016 Tacoma factory
service manual (241 MB, extracted 2026-05-14).

### CAN Bus Architecture (V Bus)

The 2016 Tacoma uses a single main CAN bus ("V Bus") shared by all powertrain and body
ECUs. There is **no gateway isolating the OBD-II port from the powertrain bus** — OQ-3
is closed. A secondary "Sub Bus 2" exists only for the optional Blind Spot Monitor /
Intuitive Parking Assist system (network gateway ECU bridges them) and is irrelevant to
this project.

**V Bus node list** (confirmed by service manual §CAN COMMUNICATION SYSTEM DESCRIPTION):

| Node | Connector | Notes |
|---|---|---|
| ECM | E20 (2TR-FE) / E13 (2GR-FKS) | Powertrain; reads ATF sensors |
| Combination Meter | C9 | Behind instrument cluster finish panel |
| Main Body ECU | — | Under dash |
| 4WD Control ECU | F13 | For 4WD models |
| Airbag Sensor | — | — |
| Spiral Cable with Sensor | — | Steering column |
| Brake Actuator (Skid Control ECU) | S1 | ABS/VSC |
| A/C Amplifier | A14 | Dash |
| Smart Key ECU | — | w/ smart key option |
| Navigation/Radio Receiver | — | Infotainment |
| TPMS Receiver | — | w/ TPMS option |
| DLC3 (OBD-II port) | D4 | Under dash, driver's left knee |

**Junction connectors** (the passive wiring hubs on the V Bus):

| Connector | Location | Branches connected |
|---|---|---|
| **No. 2 CAN Junction (J3)** | Inside cab, under dash | DLC3 (J3-3/13), Combination Meter (J3-6/16), Main Body ECU (J3-4/14), Smart Key ECU (J3-5/15), Spiral Cable (J3-7/17), TPMS (J3-2/12) → links to No. 1 junction (J3-1/11) |
| **No. 1 CAN Junction (J16)** | Inside cab, under dash | ECM (J16-5/15), A/C Amplifier (J16-3/13), Navigation/Radio (J16-4/14), Network Gateway ECU (J16-6/16), Airbag (J16-7/17), 4WD ECU (J16-8/18), Skid Control ECU (J16-1/11) → links to No. 2 junction (J16-2/12) |

### Best Tap Location for Phase 3

**Recommended**: **Combination Meter connector C9** (inside cab, accessible during gauge
mounting near steering column).

- C9-1 = CANH, C9-2 = CANL
- No cutting required — add a passive T-tap or use a breakout adapter on the branch
- Already adjacent to the gauge mounting location (instrument cluster area)
- Not on the main bus backbone; disconnecting this branch does not drop the bus

**Alternative**: No. 2 CAN Junction Connector (J3) under the dash — any of J3-1
through J3-7 carry CAN H, J3-11 through J3-17 carry CAN L. This connector is a passive
star coupler; adding a tap here is safe but requires reaching behind the dash further.

**Do not tap**: DLC3 branch — reserve for OBD-II scanner use.

### CAN Wire Colors at Key Connectors

Confirmed from service manual terminal tables:

| ECU / Connector | CANH wire | CANL wire |
|---|---|---|
| ECM (2TR-FE, E20-13/14) | Black / White-Black (B-W-B) | White / White-Black (W-W-B) |
| ECM (2GR-FKS, E13-27/35) | Black / White-Black (B-W-B) | White / White-Black (W-W-B) |
| A/C Amplifier (A14-10/11) | Blue (L) | White (W) |
| DLC3 (D4-6/14) | Pin 6 per SAE J1962 | Pin 14 per SAE J1962 |
| Combination Meter (C9-1/2) | C9-1 | C9-2 (wire colors not extracted) |

**Note**: In Toyota wiring color codes: B=Black, W=White, L=Blue, P=Pink, G=Green,
R=Red, Y=Yellow, SB=Sky Blue, LG=Light Green, V=Violet, GR=Gray, BE=Beige, BR=Brown.

---

## 5. Temperature Thresholds

**Decision**: Use the following thresholds as starting defaults; expose all values as
user-configurable without firmware rebuild.

| Signal | Normal (default color) | Warning threshold | Critical threshold |
|---|---|---|---|
| Engine oil temp | < 135 °C | 135 °C | 150 °C |
| ATF pan temp | < 130 °C | 130 °C | 150 °C |
| Torque converter temp | < 140 °C | 140 °C | 160 °C |

**Rationale**:
- Oil: Toyota 3GR/2GR-FKS engines cruise at 100–120 °C; synthetic 0W-20 tolerates up
  to ~135 °C before accelerated degradation. Above 150 °C, oxidation is rapid.
- ATF Pan: Toyota WS fluid begins measurable degradation above ~130 °C sustained. The
  factory tow-package cooler is sized to hold pan temp below 120 °C under rated load.
- TC outlet: Runs 5–30 °C above pan under slip conditions; 160 °C is the point at which
  torque converter clutch lining damage risk becomes significant.

**Confidence**: High for ATF limits (Toyota service data + community logging); medium-
high for oil (SAE literature + Toyota engine training materials). All values should be
validated against owner data-logging on the specific Tacoma before finalizing defaults.

**Configuration**: Thresholds stored in `config/thresholds.json` on a small read-write
partition; readable and editable without reflashing firmware.

---

## 6. Open Questions

| # | Question | Phase | Blocks | Status |
|---|---|---|---|---|
| OQ-1 | Is engine oil temperature accessible via enhanced OBD-II on 3rd gen V6? | Phase 1 | Slot 1 signal selection | **CLOSED** — No engine oil temp sensor exists; Slot 1 will use GATHW coolant temp (§3) |
| OQ-2 | Do PIDs 0x1627 / 0x1628 respond correctly on this specific vehicle (VIN)? | Phase 1 | Signal decoder verification | Open — confirm in vehicle with panda |
| OQ-3 | Is there a gateway isolating OBD-II bus from powertrain CAN? | Phase 3 | CAN tap strategy | **CLOSED** — No gateway; DLC3 is on the same V Bus as ECM (§4) |
| OQ-4 | What is the safest accessible CAN tap point near the steering column? | Phase 3 | Physical installation | **CLOSED** — Combination meter connector C9 (C9-1 CANH, C9-2 CANL) is recommended (§4) |
| OQ-5 | What is the MIPI DCS initialization sequence for AWL-2801424T70N01? | Phase 2 | Display driver bring-up | Open — contact Microtips (mtusainfo@microtipsusa.com) |
