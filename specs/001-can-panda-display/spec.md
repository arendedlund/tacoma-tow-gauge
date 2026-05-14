# Feature Specification: CAN Bus Gauge Display

**Feature Branch**: `001-can-panda-display`

**Created**: 2026-05-14

**Status**: Draft

**Input**: User description: "read CAN bus signals from comma.ai panda and display oil
temperature and transmission temperature on the gauge"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Engine Oil Temperature Displayed (Priority: P1)

After the vehicle is started and the gauge powers on, the driver can glance at the steering
column display and see the current engine oil temperature updating in real time.

**Why this priority**: Oil temperature is the primary motivation for the gauge and the first
data point the user wants to validate hardware and software end-to-end.

**Independent Test**: Connect the panda to a vehicle (or a CAN bus simulator), power the
gauge, and confirm a live oil temperature reading appears on the display within a few seconds
of ignition-on.

**Acceptance Scenarios**:

1. **Given** the vehicle is running and the panda is connected, **When** the gauge powers
   on, **Then** the display shows a current oil temperature reading within 5 seconds.
2. **Given** a valid oil temperature reading is available, **When** the value changes,
   **Then** the displayed value updates to reflect the new reading.
3. **Given** no oil temperature signal is received (e.g., CAN bus disconnected), **When**
   the gauge has been waiting more than 10 seconds, **Then** the display shows a clear
   "no signal" indicator rather than a stale or misleading value.

---

### User Story 2 - Transmission Temperature Displayed (Priority: P2)

The driver can see the current automatic transmission fluid temperature alongside the oil
temperature, enabling monitoring of both thermal systems during towing or spirited driving.

**Why this priority**: Transmission temperature is the second key metric; depends on the
same CAN infrastructure as US1 and can share the display layout.

**Independent Test**: With both signals available on the bus, confirm the display shows
transmission temperature updating live without affecting the oil temperature display.

**Acceptance Scenarios**:

1. **Given** both oil and transmission temperature signals are active, **When** the gauge
   is running, **Then** both temperatures are visible on the display simultaneously.
2. **Given** the transmission temperature signal is absent but oil temperature is present,
   **When** the gauge is running, **Then** oil temperature displays normally and the
   transmission slot shows a "no signal" indicator.
3. **Given** transmission temperature changes while oil temperature is stable, **When**
   the display updates, **Then** only the transmission value changes — oil temperature
   is unaffected.

---

### Edge Cases

- What happens when the CAN bus is present but the specific PID for oil or transmission
  temperature is not broadcasting (e.g., engine off, cold start delay)?
- How does the system behave when the panda USB connection is interrupted mid-session?
- What is shown if a received temperature value falls outside a physically plausible range
  (e.g., −60°C or >200°C)?
- How does the display handle the ignition-off event — does it hold the last value, go
  blank, or show a shutdown state?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read oil temperature from the vehicle CAN bus via a
  comma.ai panda interface.
- **FR-002**: The system MUST read transmission temperature from the vehicle CAN bus via
  a comma.ai panda interface.
- **FR-003**: The display MUST show both oil temperature and transmission temperature
  simultaneously within the physical display area.
- **FR-004**: The system MUST refresh displayed temperature values at a rate that feels
  live to the driver (perceived as real-time).
- **FR-005**: The system MUST show a clear "no signal" or fault indicator for any
  temperature channel that has not received a valid reading within a configurable timeout.
- **FR-006**: The system MUST reject and not display temperature values that fall outside
  a physically plausible range for each sensor type.
- **FR-007**: The system MUST handle ignition-off gracefully without data corruption or
  a frozen display state.
- **FR-008**: The system MUST support adding additional CAN-sourced gauges in future
  without modifying existing oil or transmission temperature display logic.

### Key Entities

- **CAN Frame**: A raw message received from the panda; identified by arbitration ID,
  contains payload bytes from which signal values are decoded.
- **Gauge Signal**: A named, human-readable value (e.g., "Oil Temp") derived from one or
  more CAN frame fields; has a unit, plausibility range, and staleness timeout.
- **Display Slot**: A region of the physical screen allocated to one Gauge Signal; renders
  the current value or a fault state.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Oil temperature appears on the display within 5 seconds of the first valid
  CAN frame being received after ignition-on.
- **SC-002**: Transmission temperature appears on the display within 5 seconds of the
  first valid CAN frame being received after ignition-on.
- **SC-003**: Both temperature readings update visibly within 2 seconds of the underlying
  CAN signal changing by a meaningful amount.
- **SC-004**: A "no signal" state is shown within 10 seconds of a channel going silent,
  with no stale value remaining on screen.
- **SC-005**: Adding a third gauge type requires no changes to existing oil or
  transmission temperature code paths (verified by code review).

## Assumptions

- The Toyota Tacoma broadcasts oil temperature and transmission temperature on the CAN bus
  at known arbitration IDs; the exact PIDs will be confirmed during planning/research.
- The comma.ai panda connects to the host microcontroller via USB; the host reads frames
  using the panda's published USB protocol.
- The display is the Microtips AWL-2801424T70N01 (280×1424 px, portrait bar orientation)
  connected via MIPI.
- Temperature values will be displayed in Celsius; a unit toggle is out of scope for v1.
- A bench CAN bus simulator or OBD-II loopback adapter is available for development
  testing without a physical vehicle.
- The panda firmware in use supports passive CAN sniffing on the OBD-II port without
  sending frames to the bus.
