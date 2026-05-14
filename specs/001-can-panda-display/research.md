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

## 3. Tacoma CAN PIDs — Engine Oil Temperature

**Decision**: UNRESOLVED — requires in-vehicle verification as the first task of Phase 1.

**Finding**: Community research is conflicting. Multiple sources indicate the 3rd gen
Tacoma V6 has no dedicated engine oil temperature sensor — the oil pressure circuit uses
an on/off switch (not a transducer), and no confirmed Mode 22 PID for oil temperature
exists in community documentation or the commaai/opendbc Toyota DBC files.

However, Toyota engine ECMs for this generation do internally estimate oil temperature
from coolant temperature, engine load, and run time. This calculated value may be
exposed as an enhanced PID (Mode 22 on header `0x7E0`) on some variants.

**Action required in Phase 1**: During the Cabana capture session, specifically attempt
to query `0x7E0` with Mode 22 and scan for any temperature-range responses. Cross-
reference with Toyota TIS documentation if access is obtained.

**Contingency if oil temp is not accessible**: Replace the oil temperature gauge slot
with an alternative signal that is confirmed accessible (e.g., engine coolant
temperature, intake air temperature, or a calculated derivative). This decision gates
display layout finalization.

---

## 4. CAN Bus Tap Location (Phase 3+)

**Decision**: DEFERRED to Phase 3 planning. Requires Toyota TIS wiring diagram access
and physical vehicle inspection.

**Finding**: No reliable community documentation exists for non-OBD-II CAN tap points
on the 3rd gen Tacoma. The OBD-II port (DLC3, under the dashboard) is the well-known
access point, but the project requires that port to remain free.

**Known leads to investigate in Phase 3**:
- **DLC1**: A second diagnostic connector exists in the engine bay on some Toyota models;
  needs confirmation on 3rd gen Tacoma and verification it exposes the same bus.
- **Instrument cluster connector**: The cluster has CAN H/L pins; accessible from behind
  the dashboard without cutting into harness.
- **TCM (transmission control module) connector**: Directly on the powertrain CAN bus;
  requires locating the TCM (typically under the hood or under the center console).
- **Gateway module risk**: Newer Toyotas sometimes use a gateway that isolates the
  OBD-II diagnostic bus from the powertrain CAN bus. If present, tapping at the cluster
  or TCM may expose a different (or the same) physical bus than the OBD-II port. Needs
  confirmation via TIS wiring diagram for the specific model year.

**Authoritative source**: Toyota TIS (techinfo.toyota.com) provides full electrical
wiring diagrams for $15/48 hours — recommended purchase at the start of Phase 3.

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

## 6. Open Questions Requiring Hardware Resolution

| # | Question | Phase | Blocks |
|---|---|---|---|
| OQ-1 | Is engine oil temperature accessible via enhanced OBD-II on 3rd gen V6? | Phase 1 | Display layout finalization |
| OQ-2 | Do PIDs 0x1627 / 0x1628 respond correctly on this specific vehicle (VIN)? | Phase 1 | Signal decoder implementation |
| OQ-3 | Is there a gateway module that isolates OBD-II bus from powertrain CAN? | Phase 3 | CAN tap strategy |
| OQ-4 | What is the safest accessible CAN tap point near the steering column? | Phase 3 | Physical installation design |
| OQ-5 | What is the MIPI DCS initialization sequence for AWL-2801424T70N01? | Phase 2 | Display driver bring-up |
