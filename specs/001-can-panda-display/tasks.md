# Tasks: CAN Bus Gauge Display

**Input**: Design documents from `specs/001-can-panda-display/`

**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅ quickstart.md ✅

**Tests**: No automated test suite in v1 (per plan.md). Validation is manual hardware + virtual CAN injection.

**Organization**: Tasks grouped by user story. Tasks marked `[HW]` are hardware-gated and cannot begin until the specified hardware is available. All other tasks run on macOS today.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared state dependencies)
- **[Story]**: User story this task belongs to
- **[HW]**: Hardware-gated — requires physical device listed in the task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create project skeleton so all subsequent tasks have a landing place.

- [ ] T001 Create project directory structure: `src/can/`, `src/signals/`, `src/display/`, `src/config/`, `config/`, `systemd/`, `tools/`
- [ ] T002 [P] Create `requirements.txt` with `python-can`, `pygame`, `pillow`, `cantools` pinned to current stable versions
- [ ] T003 [P] Create `src/can/__init__.py`, `src/signals/__init__.py`, `src/display/__init__.py` (empty package markers)

**Checkpoint**: `python3 -c "import can, pygame, cantools"` succeeds in venv

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model and config layer — required before any user story can run.

**⚠ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T004 Implement `SignalState` enum (`WAITING`, `NORMAL`, `WARNING`, `CRITICAL`, `NO_SIGNAL`, `FAULT`) in `src/signals/decoder.py`
- [ ] T005 Implement `GaugeSignal` dataclass with `on_receive_frame(decoded_value)` and `on_tick()` state transition logic in `src/signals/decoder.py` (see data-model.md §GaugeSignal)
- [ ] T006 [P] Implement `src/config/loader.py` — reads `config/signals.json` and `config/thresholds.json`, instantiates `GaugeSignal` objects with thresholds; raises on missing required fields
- [ ] T007 [P] Create `config/signals.json` with ATF pan (PID 0x1627) and TC outlet (PID 0x1628) entries per signal-contract.md; add oil temp placeholder entry with `"status": "pending-OQ-1"`
- [ ] T008 [P] Create `config/thresholds.json` with default thresholds per research.md §5: ATF pan warn 130°C/crit 150°C; TC outlet warn 140°C/crit 160°C; oil temp warn 135°C/crit 150°C; all staleness 10s
- [ ] T009 Implement `SignalDecoder` decode functions for ATF pan and TC outlet in `src/signals/decoder.py`: formula `((A*459/255) + (B*1.6/255) - 40 - 32) * 5/9`; bytes from response payload positions 3 and 4

**Checkpoint**: `python3 -c "from src.config.loader import load_signals; sigs = load_signals('config/'); print(sigs)"` prints three GaugeSignal objects in WAITING state

---

## Phase 3: User Story 1 — CAN Frame Identification (Priority: P1)

**Goal**: Produce verified signal definitions (frame IDs, byte positions, formulas) for all three temperature channels from a live Tacoma capture session.

**Independent Test**: Run `tools/capture_verify.py` with panda connected to vehicle OBD-II port; decoded ATF pan and TC outlet values rise monotonically during a cold-start warmup.

**Hardware gate**: panda (ordered; ETA ~1 week). Tools T010–T012 can be written and tested against the virtual bus immediately.

### Implementation

- [ ] T010 [P] [US1] Create `tools/capture_verify.py` — sends Mode 22 requests for PIDs 0x1627 and 0x1628 to header 0x7E1 via panda USB; prints decoded ATF pan and TC outlet °C values in real time to stdout
- [ ] T011 [P] [US1] Create `tools/monitor_broadcast.py` — passive listener for broadcast frames 0x3BC (`BV_THOCL`) and 0x3C1 (`GATHW`) using cantools + local DBC (`~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc`); prints decoded values alongside timestamp
- [ ] T012 [P] [US1] Create `tools/dbc_inspect.py` — CLI utility: given a frame ID, loads the Toyota DBC and prints all signals with bit positions, scale, offset, and a sample decode; used for ad-hoc exploration during capture session
- [ ] T013 [HW: panda + vehicle] [US1] Run `tools/capture_verify.py` and `tools/monitor_broadcast.py` simultaneously in the vehicle; record which signals respond, their raw byte positions, and cross-check decoded values against a known reference thermometer during warmup
- [ ] T014 [US1] Update `config/signals.json` with Phase 1 verified signal definitions: confirm or correct ATF and TC outlet byte positions; resolve oil temp slot (populate if accessible, or substitute `GATHW` coolant temp from 0x3C1); remove `pending-OQ-1` placeholder
- [ ] T015 [US1] If `BV_THOCL` broadcast is verified in T013, update `contracts/signal-contract.md` to add optional `broadcast_frame_id` field for passively-received signals; update `config/signals.json` schema note accordingly

**Checkpoint**: `config/signals.json` has three complete, verified entries with no placeholder fields

---

## Phase 4: User Story 2 — Proof-of-Concept Demo (Priority: P2)

**Goal**: CM5 + panda USB → Microtips display shows all three live temperatures with correct color states. Full signal-to-pixel pipeline validated in vehicle before any permanent modifications.

**Independent Test**: Bench rig in vehicle, panda on OBD-II, engine running — all three slots update within 2s; warning color appears when ATF temp rises into the warning band.

**Hardware gate for T023–T026**: CM5 + CM5 IO Board + Microtips AWL-2801424T70N01 + MIPI ribbon. T017–T022 run on macOS today.

### Software (no hardware required)

- [ ] T016 [P] [US2] Implement `src/can/reader.py` — background thread; opens `can.Bus` (interface configurable: `panda` or `virtual`); filters frames by `arbitration_id`; calls registered `SignalDecoder.decode` and updates corresponding `GaugeSignal` under a threading lock
- [ ] T017 [P] [US2] Implement `src/display/slot.py` — `DisplaySlot` dataclass with `Rect` position, label string, and `render(surface, gauge_signal)` method; maps `SignalState` → pygame color per display-contract.md color table
- [ ] T018 [P] [US2] Create `tools/inject_virtual_can.py` — injects synthetic Mode 22 response frames for all three signals on `python-can` virtual bus `channel='test'`; supports CLI args for temperature value overrides to exercise NORMAL/WARNING/CRITICAL state transitions
- [ ] T019 [US2] Implement `src/display/renderer.py` — pygame init; `display.set_mode((1424, 280))`; three-slot layout per display-contract.md (x=0/475/950, each ~474×280); render loop at 30fps reading `GaugeSignal` state each frame; supports `--windowed` flag (macOS) and `/dev/fb0` framebuffer (CM5)
- [ ] T020 [US2] Implement `src/main.py` — argument parsing (`--config`, `--windowed`, `--bus-interface`); instantiates config, signals, CAN reader thread, and renderer; wires graceful shutdown on SIGTERM and keyboard interrupt
- [ ] T021 [US2] Local integration validation — run `python3 src/main.py --config config/ --windowed --bus-interface virtual` with `tools/inject_virtual_can.py` running; confirm all three slots render, update, and cycle through WAITING → NORMAL → WARNING → CRITICAL → NO_SIGNAL states

### Hardware bringup

- [ ] T022 [HW: CM5 + CM5 IO Board] [US2] Flash Raspberry Pi OS Lite 64-bit on CM5; install Python dependencies per quickstart.md §1–2; confirm `python3 src/main.py --windowed` runs on CM5 HDMI output
- [ ] T023 [HW: Microtips display + MIPI ribbon + DCS init from Microtips — OQ-5] [US2] Add Microtips Device Tree overlay to `/boot/config.txt` on CM5; confirm display initialises at 1424×280 (framebuffer visible via `fbset`)
- [ ] T024 [HW: panda + vehicle] [US2] Run bench rig in vehicle: panda → CM5 USB → Microtips display; confirm all three temperature slots show live values within 5s of engine start; confirm NO_SIGNAL state appears within 10s of panda disconnect

**Checkpoint**: Full demo video showing three live temperatures in vehicle with warning color change

---

## Phase 5: User Story 3 — Standalone CAN Integration (Priority: P3)

**Goal**: Panda removed. CM5 reads CAN directly via MCP2515 SPI + TJA1050 transceiver at a non-OBD-II tap point. OBD-II port confirmed free.

**Independent Test**: Panda disconnected, CM5 on direct CAN tap, engine running — all three temps live; diagnostic scanner on OBD-II port operates normally simultaneously.

**Hardware gate for T028–T031**: MCP2515 module + Toyota TIS access + vehicle inspection.

### Software (no hardware required)

- [ ] T025 [P] [US3] Update `src/can/reader.py` to support SocketCAN interface alongside panda: detect `--bus-interface socketcan` and open `can.interface.Bus('can0', interface='socketcan')`; no changes to decoder or display code
- [ ] T026 [P] [US3] Update `config/signals.json` to support broadcast frame mode if BV_THOCL was verified in US1 — add `source: "broadcast"` field and `frame_id` in place of `request_header`/`obd_mode`/`obd_pid`; update `src/can/reader.py` to handle passive-listen signals (no request sent)

### Hardware bringup

- [ ] T027 [HW: MCP2515 SPI module + TJA1050 transceiver] [US3] Wire MCP2515 to CM5 IO Board SPI/GPIO; add `dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25` to `/boot/config.txt`; confirm `ip link show can0` succeeds
- [ ] T028 [HW: Toyota TIS $15/48h] [US3] Purchase TIS access; download wiring diagram for 3rd gen Tacoma; identify CAN H/L wire colors and connector pin numbers at the instrument cluster or TCM connector near the steering column
- [ ] T029 [HW: vehicle + wire tap] [US3] Tap CAN H/L at the identified location; connect to MCP2515; run `candump can0` to confirm frames appear; verify no ADAS or safety system interference
- [ ] T030 [HW: vehicle] [US3] Run `python3 src/main.py --config config/ --bus-interface socketcan` in vehicle; confirm all three temps live; plug OBD-II scanner simultaneously and confirm scanner and gauge both work

**Checkpoint**: Gauge running on direct CAN; panda absent; OBD-II port confirmed free under simultaneous scanner use

---

## Phase 6: User Story 4 — Permanent Installation (Priority: P4)

**Goal**: Key-on powers the gauge automatically. Enclosure printed and installed. No loose wiring visible.

**Independent Test**: Cold start from parking lot — display illuminates within 10s, shows all three temps through warmup, shuts down cleanly at key-off.

**Hardware gate for T034–T039**: 12V→5V DC-DC converter + fuse tap + PETG filament + enclosure print.

### Software (no hardware required)

- [ ] T031 [P] [US4] Create `systemd/gauge.service` — `Type=simple`; `After=multi-user.target`; `Environment=SDL_FBDEV=/dev/fb0`; `ExecStart=/opt/gauge-env/bin/python3 /opt/gauge/src/main.py --config /opt/gauge/config`; `Restart=on-failure`
- [ ] T032 [P] [US4] Create `tools/setup_readonly_fs.sh` — configures overlayFS read-only root on Raspberry Pi OS; adds small RW partition mount for `/opt/gauge/config`; documents revert procedure

### Hardware bringup

- [ ] T033 [HW: 12V→5V automotive DC-DC converter + blade fuse tap] [US4] Wire DC-DC converter to WSH fuse tap in interior fuse box; verify 5V output under load; connect to CM5 power input
- [ ] T034 [HW: CM5] [US4] Apply overlayFS read-only root (T032 script); enable `gauge.service`; test abrupt power-off and power-on cycle — confirm no data corruption and clean boot
- [ ] T035 [HW: CM5] [US4] Measure boot-to-first-frame time; tune systemd service order and disable unused services until boot ≤10s from power-on (SC-006 target)
- [ ] T036 [HW: PETG filament + 3D printer] [US4] Print steering column clamshell with Microtips display cutout; test-fit display and CM5 IO Board in enclosure before permanent mount
- [ ] T037 [HW: vehicle + enclosure] [US4] Install enclosure on steering column; route wiring behind dash; mount CM5; dress all wiring with loom; verify OBD-II port fully accessible; run final acceptance drive cycle

**Checkpoint**: Vehicle started cold, gauge illuminates ≤10s, shows all three temps through full warmup, shuts down cleanly — no manual steps required

---

## Polish & Cross-Cutting Concerns

- [ ] T038 [P] Update `quickstart.md` with any deviations from planned setup discovered during hardware bringup (actual DT overlay params, validated dependency versions)
- [ ] T039 [P] Update `research.md §2a` with Phase 1 capture findings — confirm or refute BV_THOCL as ATF broadcast; record actual OBD-II PID byte positions verified on this VIN
- [ ] T040 [P] Performance audit: log actual boot time, render frame rate, and CAN-to-display latency against SC-003 (≤2s), SC-006 (≤10s boot), and 30fps target

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)        → no dependencies; start immediately
Phase 2 (Foundational) → requires Phase 1 completion
Phase 3 (US1)          → requires Phase 2; T010–T012 start immediately; T013+ need panda
Phase 4 (US2)          → requires Phase 2; T016–T021 start immediately; T022+ need hardware
Phase 5 (US3)          → requires US1 complete (verified signal config); T025–T026 can start now
Phase 6 (US4)          → requires US3 complete; T031–T032 can start now
Polish                 → runs after corresponding story complete
```

### User Story Dependencies

- **US1 (P1)**: Foundational complete → tools written immediately; capture session when panda arrives
- **US2 (P2)**: US1 signal config finalized → software can start immediately; hardware bringup after CM5 + display arrive
- **US3 (P3)**: US2 bench-tested → SocketCAN changes; hardware bringup needs MCP2515 + TIS access
- **US4 (P4)**: US3 validated in vehicle → systemd + overlayFS; hardware bringup needs DC-DC + enclosure

### What Can Start Today (No Hardware)

T001–T012 (Setup + Foundational), T010–T012 (US1 tools), T016–T021 (US2 software), T025–T026 (US3 software), T031–T032 (US4 software) — approximately 22 of 40 tasks.

---

## Parallel Opportunities

### Phase 2 (run together)

```
T006 config/loader.py
T007 config/signals.json       ← all three in parallel
T008 config/thresholds.json
```

### US1 tools (run together after T002)

```
T010 tools/capture_verify.py
T011 tools/monitor_broadcast.py   ← all three in parallel
T012 tools/dbc_inspect.py
```

### US2 software (run together after Phase 2)

```
T016 src/can/reader.py
T017 src/display/slot.py          ← in parallel
T018 tools/inject_virtual_can.py
```

---

## Implementation Strategy

### MVP (US2 running locally on macOS — no hardware)

1. Phase 1: Setup (T001–T003)
2. Phase 2: Foundational (T004–T009)
3. US1 tools (T010–T012)
4. US2 software (T016–T021)
5. **Validate**: `python3 src/main.py --config config/ --windowed` + virtual CAN injector → full display visible on desktop

### Incremental Hardware Delivery

1. **Panda arrives** → Run T013 in vehicle; finalize T014–T015; US1 complete
2. **CM5 + display arrive** → T022–T024; US2 bench demo complete
3. **MCP2515 + TIS** → T027–T030; US3 complete; panda retired
4. **DC-DC + enclosure** → T033–T037; US4 complete; permanent installation

---

## Notes

- `[P]` = different files, no shared incomplete dependencies — safe to parallelise
- `[HW]` tasks are blocked by physical hardware; plan and write their software counterparts first
- No automated tests in v1; manual validation via virtual CAN injector + hardware bench testing
- Each checkpoint is a natural pause-and-validate moment before proceeding to the next story
- Signal config (`config/signals.json`) is the integration point between US1 and US2 — US2 software can be built against the placeholder entries and swapped to verified values after US1
