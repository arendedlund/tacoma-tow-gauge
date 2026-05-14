# Feature Specification: CAN Bus Gauge Display

**Feature Branch**: `001-can-panda-display`

**Created**: 2026-05-14

**Status**: Draft

**Input**: User description: "read CAN bus signals from comma.ai panda and display oil
temperature and transmission temperature on the gauge"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CAN Frame Identification (Priority: P1)

Using a comma.ai panda connected to the Tacoma's OBD-II port and comma.ai Cabana software,
the developer logs live CAN traffic and decodes the frames that carry engine oil temperature,
transmission pan temperature, and torque converter temperature. The output is a verified
list of arbitration IDs, byte positions, and decoding formulas for each signal.

**Why this priority**: Nothing else can be built until the exact CAN signals are confirmed.
Community PID data for Tacoma is unverified; this phase produces ground-truth data from
the actual vehicle.

**Independent Test**: Sit in the vehicle with the engine running, connect the panda, capture
frames in Cabana, and identify all three temperature signals by cross-referencing decoded
values against known temperatures (e.g., cold-start warmup, engine at operating temp).

**Acceptance Scenarios**:

1. **Given** the panda is connected to the OBD-II port and the engine is running, **When**
   Cabana is used to log CAN traffic, **Then** frames containing oil temperature data are
   identified and their arbitration ID, byte positions, and decoding formula are recorded.
2. **Given** the same capture session, **When** the transmission is at operating temperature,
   **Then** frames for both pan temperature and torque converter temperature are identified
   with their arbitration IDs, byte positions, and decoding formulas.
3. **Given** the decoded formulas are applied to a live capture, **When** the vehicle
   temperature rises during a warmup cycle, **Then** the decoded values change in a
   physically plausible and monotonically increasing direction.

---

### User Story 2 - Proof-of-Concept Demo (Priority: P2)

With the CAN signals identified in US1, a microcontroller board is connected to the
Microtips display and to the panda via USB. The gauge shows oil temperature, transmission
pan temperature, and torque converter temperature updating in real time. This validates
the full signal-to-display pipeline before any permanent installation.

**Why this priority**: De-risks the display driver, MCU selection, and signal decoding
integration together in a bench/vehicle setting before committing to enclosure design.
The panda remains the CAN source to keep the demo reversible.

**Independent Test**: Place the bench rig in the vehicle, connect the panda to OBD-II,
start the engine, and confirm all three temperatures appear on the display and change
during a warmup cycle — with no vehicle modifications made.

**Acceptance Scenarios**:

1. **Given** the panda is connected to OBD-II and the MCU rig is powered, **When** the
   engine is started, **Then** all three temperature values appear on the display within
   5 seconds of the first valid CAN frame.
2. **Given** the display is running, **When** any temperature value changes, **Then** the
   corresponding slot updates within 2 seconds and the other slots are unaffected.
3. **Given** the panda is disconnected mid-session, **When** the timeout elapses, **Then**
   all three slots show a "no signal" indicator with no stale values remaining.

---

### User Story 3 - Standalone CAN Integration (Priority: P3)

The panda is removed from the design. The MCU connects directly to the vehicle CAN bus
at a tap point that is not the OBD-II port, leaving the OBD-II port free for diagnostic
tools. The display continues to show the same three temperatures with identical behavior
to US2.

**Why this priority**: Makes the device self-contained and frees the OBD-II port. The
tap location and wiring method require research — this is the primary unknown of the
project.

**Independent Test**: With the panda disconnected and the MCU wired to a direct CAN tap,
start the vehicle and confirm all three temperatures display correctly. Plug a diagnostic
scanner into the OBD-II port simultaneously and confirm it operates normally.

**Acceptance Scenarios**:

1. **Given** the MCU is wired to a direct CAN tap (not OBD-II), **When** the vehicle is
   started, **Then** all three temperatures appear on the display within 5 seconds,
   identical in behavior to US2.
2. **Given** the direct CAN tap is in use, **When** a diagnostic scanner is connected to
   the OBD-II port, **Then** the scanner operates normally and the gauge display is
   unaffected.
3. **Given** the CAN tap connection is lost, **When** the timeout elapses, **Then** the
   display shows "no signal" on all affected channels without freezing.

---

### User Story 4 - Permanent Installation (Priority: P4)

A new steering column clamshell is printed with a cutout sized to the Microtips display.
The MCU is mounted permanently in the vehicle. Power is drawn from the WSH (windshield
washer) key-on accessory circuit. When the key is turned on, the gauge powers up and
begins displaying temperatures automatically. The installation is seamless — no loose
wiring, no bench rig, no OBD-II dongle visible.

**Why this priority**: The final user-facing deliverable. Depends on all prior phases
being proven out.

**Independent Test**: Start the vehicle from cold. The gauge powers on automatically,
shows all three temperatures, and updates through the warmup cycle. No other vehicle
function is affected. The OBD-II port is unobstructed.

**Acceptance Scenarios**:

1. **Given** the key is turned to the on position, **When** the WSH circuit powers up,
   **Then** the gauge display illuminates and begins showing temperatures within 10 seconds,
   with no manual intervention required.
2. **Given** the key is turned off, **When** the WSH circuit loses power, **Then** the
   display shuts down cleanly with no frozen frame or corrupted state on next power-on.
3. **Given** the installation is complete, **When** inspected, **Then** the display is
   flush-mounted in the clamshell, all wiring is routed out of sight, and the OBD-II
   port under the dashboard is fully accessible.

---

### Edge Cases

- What happens when a CAN signal is present during cold start but the value is outside
  the plausible operating range (sensor not yet warmed, ECU reporting default values)?
- How does the system behave when the CAN bus is present but a specific signal is not
  yet broadcasting (e.g., transmission signals absent until fluid warms up)?
- How does the display handle the ignition-off event — hold last value, go blank, or
  show a shutdown state?
- If the direct CAN tap (US3) is on a bus segment that is not active at key-on, when
  does data first appear?
- What is the physical CAN tap location, and does tapping it affect any ADAS or safety
  systems on the Tacoma?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST identify the arbitration IDs, byte positions, and decoding
  formulas for oil temperature, transmission pan temperature, and torque converter
  temperature from live Tacoma CAN traffic.
- **FR-002**: The system MUST read oil temperature from the vehicle CAN bus via a CAN
  transceiver on the controller board.
- **FR-003**: The system MUST read transmission pan temperature from the vehicle CAN bus
  via a CAN transceiver on the controller board.
- **FR-004**: The system MUST read torque converter temperature from the vehicle CAN bus
  via a CAN transceiver on the controller board.
- **FR-005**: The display MUST show oil temperature, transmission pan temperature, and
  torque converter temperature simultaneously, each in a distinct labelled slot.
- **FR-006**: The system MUST refresh displayed temperature values at a rate that feels
  live to the driver (perceived as real-time).
- **FR-007**: The system MUST show a clear "no signal" or fault indicator for any channel
  that has not received a valid reading within a configurable timeout.
- **FR-008**: The system MUST reject and not display values that fall outside a physically
  plausible range for each signal.
- **FR-009**: The CAN tap MUST NOT use the OBD-II port — that port MUST remain free for
  diagnostic tools in the finished installation.
- **FR-010**: The device MUST power on automatically when the WSH key-on circuit
  energises and shut down cleanly when it de-energises.
- **FR-011**: The system MUST handle ignition-off gracefully without data corruption or
  a frozen display state on next power-on.
- **FR-012**: The system MUST support adding additional CAN-sourced gauges in future
  without modifying existing temperature display logic.

### Key Entities

- **CAN Frame**: A raw message received from the CAN bus; identified by arbitration ID,
  contains payload bytes from which signal values are decoded.
- **Gauge Signal**: A named value (e.g., "Oil Temp") derived from CAN frame fields; has a
  unit, plausible range, decoding formula, and staleness timeout.
- **Display Slot**: A region of the physical screen allocated to one Gauge Signal; renders
  the current value or a fault state.
- **CAN Tap**: The physical point on the vehicle wiring harness where the MCU connects
  to the CAN bus without using the OBD-II port.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three temperature signals are identified and their decoding formulas
  verified against a live vehicle warmup cycle (values change plausibly from cold to hot).
- **SC-002**: All three temperatures appear on the display within 5 seconds of the first
  valid CAN frame after power-on.
- **SC-003**: All three temperature readings update visibly within 2 seconds of the
  underlying CAN signal changing by a meaningful amount.
- **SC-004**: A "no signal" state appears within 10 seconds of a channel going silent,
  with no stale value remaining on screen.
- **SC-005**: With the finished installation running, a diagnostic scanner plugged into
  the OBD-II port operates normally.
- **SC-006**: The display powers on within 10 seconds of key-on and shuts down cleanly
  at key-off, with no manual steps required.
- **SC-007**: Adding a fourth gauge type requires no changes to existing temperature
  display code paths (verified by code review).

## Assumptions

- The Toyota Tacoma broadcasts oil temperature, transmission pan temperature, and torque
  converter temperature on the CAN bus; preliminary community research suggests OBD-II
  request header 07E0/07E1 with PID 2182 may carry ATF temperature data, but this is
  unverified and must be confirmed by panda capture before implementation.
- A non-OBD-II CAN tap location exists on the Tacoma that is accessible and safe to use;
  the exact location and method require research during Phase 3 planning.
- The production hardware consists of a microcontroller board (TBD during planning) with
  an integrated or attached CAN transceiver and a MIPI interface driving the display.
- In Phase 2 (demo), the panda is the CAN source connected via USB to the MCU; in Phase 3
  onward, the MCU connects directly to the vehicle CAN bus.
- The comma.ai panda is a development-only tool (Phases 1–2); it is not part of the
  finished installation.
- The display is the Microtips AWL-2801424T70N01 (280×1424 px, portrait bar orientation)
  connected via MIPI.
- Power is supplied from the WSH (windshield washer) key-on accessory circuit, 25A fused;
  device draw is expected to be well under 1A.
- Temperature values will be displayed in Celsius; a unit toggle is out of scope for v1.
- The 3D-printed clamshell design and MCU mounting location are out of scope for the
  software specification; they are mechanical deliverables of Phase 4.
