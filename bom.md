# Bill of Materials — Tacoma Tow Gauge

**Last updated**: 2026-05-14

---

## Display

**Orientation**: Landscape — the display mounts with its long axis running horizontally
behind the steering wheel.

**Physical constraints** (from clamshell clearances):
- Max height (vertical): ~38mm (1.5") — limited by instrument cluster sightline
- Max width (horizontal): ~279mm (11") — limited by clamshell span

**Selected display**: Microtips AWL-2801424T70N01

| Spec | Value |
|---|---|
| Resolution (landscape) | 1424 × 280 px |
| Active area | 170.9mm wide × 33.6mm tall (6.7" × 1.3") |
| Overall outline | 181.5mm wide × 38.2mm tall — fits within both constraints |
| Interface | MIPI DSI |
| Driver | Custom Device Tree overlay required (DCS init sequence from Microtips) |

The Microtips panel is the only reviewed option that satisfies the 38mm height limit.
The Waveshare 11.9" (next narrowest bar display) is 58mm tall in landscape — 53% over
the limit. The Microtips at 38.2mm is essentially flush with the 1.5" constraint.

**Action required**: Contact Microtips (mtusainfo@microtipsusa.com, 1-888-499-8477) to
request the MIPI DCS initialization command sequence for AWL-2801424T70N01 and confirm
pricing and stock. This is needed for Phase 2 display bring-up.

---

## Full BOM

### Phase 1 — CAN Reverse Engineering

| # | Item | Qty | Est. Unit Cost | Est. Total | Source | Status |
|---|---|---|---|---|---|---|
| 1 | comma.ai panda | 1 | — | — | comma.ai | **ORDERED** |
| 2 | Laptop + USB-A port (or hub) | 1 | — | — | Already have | Have |
| 3 | Cabana software | 1 | Free | — | GitHub (open source) | Free |

*Phase 1 requires no additional purchases. Begin as soon as panda arrives.*

---

### Phase 2 — Proof-of-Concept Demo

| # | Item | Qty | Est. Unit Cost | Est. Total | Source | Notes |
|---|---|---|---|---|---|---|
| 4 | Raspberry Pi CM5 (1GB or 2GB) | 1 | ~$45–65 | ~$55 | CanaKit | 1GB sufficient for this project |
| 5 | CM5 IO Board | 1 | ~$40 | ~$40 | CanaKit (bundle) | Often sold as kit with CM5 |
| 6 | Microtips AWL-2801424T70N01 display | 1 | TBD | TBD | Microtips directly | Contact before ordering CM5 |
| 7 | MIPI DSI ribbon cable (15-pin FPC, ~50–160mm) | 1–2 | ~$5 | ~$10 | Amazon | Check pitch and length vs CM5 IO Board DSI port |
| 8 | MicroSD card 32GB+ (A2 rated) | 1 | ~$12 | ~$12 | Amazon | For OS |
| 9 | USB-C power supply 5V/3A+ | 1 | ~$15 | ~$15 | Amazon | Bench power for CM5 |
| 10 | USB-A to USB-C cable (for panda) | 1 | ~$8 | ~$8 | Amazon | panda → CM5 USB host |
| 11 | Dupont jumper wires (M-F, 20cm) | 1 pack | ~$8 | ~$8 | Amazon | Bench wiring |
| 12 | Mini-HDMI to HDMI cable | 1 | ~$8 | ~$8 | Amazon | CM5 IO board setup/debugging |
| **Phase 2 subtotal** | | | | **~$161–181** | | |

---

### Phase 3 — Direct CAN Integration

| # | Item | Qty | Est. Unit Cost | Est. Total | Source | Notes |
|---|---|---|---|---|---|---|
| 13 | Toyota TIS 48-hour access | 1 | $15 | $15 | techinfo.toyota.com | Buy when ready for Phase 3; wiring diagrams for tap location |
| 14 | MCP2515 CAN controller + TJA1050 SPI module | 2 | ~$7 | ~$14 | Amazon | One primary, one spare; 16 MHz crystal recommended |
| 15 | CAN bus tap connector | TBD | TBD | ~$20–50 | TBD | Depends on tap location found via TIS; likely posi-tap or Deutsch connector |
| 16 | Automotive-grade hookup wire (22 AWG, various colors) | 1 roll | ~$15 | ~$15 | Amazon | CAN H, CAN L, power lines |
| 17 | 120Ω termination resistor (if needed) | 2 | <$1 | <$2 | Electronics supplier | CAN bus termination; only if tapping an unterminated stub |
| **Phase 3 subtotal** | | | | **~$66–96** | | |

---

### Phase 4 — Permanent Installation

| # | Item | Qty | Est. Unit Cost | Est. Total | Source | Notes |
|---|---|---|---|---|---|---|
| 18 | Automotive 12V→5V DC-DC converter, 3A+ | 1 | ~$25 | ~$25 | Amazon | Must be automotive-grade; handles 8–16V input, ignition spikes |
| 19 | Blade fuse tap (mini or standard ATM, per Tacoma fuse box) | 1 | ~$8 | ~$8 | Amazon | Taps WSH circuit in interior fuse box |
| 20 | Heat shrink tubing assortment | 1 pack | ~$8 | ~$8 | Amazon | |
| 21 | Automotive ring terminals + butt splices | 1 pack | ~$8 | ~$8 | Amazon | |
| 22 | Wire loom / split conduit (1/4" and 3/8") | 1m each | ~$8 | ~$8 | Amazon | Route wiring neatly behind dash |
| 23 | PETG filament 1kg spool | 1 | ~$25 | ~$25 | Amazon/local | Clamshell print; PETG for heat resistance |
| 24 | M2/M3 mounting screws and standoffs assortment | 1 kit | ~$12 | ~$12 | Amazon | Mounting CM5 IO board and display |
| 25 | Velcro or 3M dual-lock tape | 1 pack | ~$10 | ~$10 | Amazon | Temporary/semi-permanent MCU mount |
| **Phase 4 subtotal** | | | | **~$104** | | |

---

## Total Estimate

| Phase | Subtotal |
|---|---|
| Phase 1 | $0 (panda already ordered) |
| Phase 2 | ~$161–181 |
| Phase 3 | ~$66–96 |
| Phase 4 | ~$104 |
| **Grand total** | **~$331–381** |

*Excludes panda cost (already purchased) and any 3D printer access costs.*

---

## Purchase Schedule

### Order Now

- [ ] **Contact Microtips** for AWL-2801424T70N01 pricing, stock, and DCS init sequence — gates display bring-up
- [ ] CM5 + CM5 IO Board (CanaKit bundle)
- [ ] Chosen display
- [ ] MicroSD card 32GB A2
- [ ] USB-C power supply
- [ ] USB-A to USB-C cable
- [ ] Mini-HDMI cable
- [ ] Dupont jumper wires

**Why now**: CM5 setup and display driver bring-up can start immediately and run in
parallel with Phase 1 (CAN RE). Getting the display working on the CM5 is the longest
technical task — start it early.

### When Panda Arrives (~1 week)

- [ ] Begin Phase 1: connect panda to Tacoma OBD-II, capture with Cabana
- [ ] Verify ATF pan temp PID 0x1627 and TC outlet PID 0x1628 respond
- [ ] Determine if engine oil temperature is accessible via enhanced OBD-II (OQ-1)
- [ ] No new purchases required

### After Phase 1 Complete (PIDs Verified)

- [ ] MCP2515 SPI CAN modules ×2 (can order earlier if impatient — they're cheap)
- [ ] Begin Phase 2 demo integration using panda + CM5 + display

### When Starting Phase 3 Planning

- [ ] Purchase Toyota TIS 48h access ($15) — download and save all relevant wiring
  diagrams for the specific model year during the 48h window
- [ ] Determine CAN tap location, then order appropriate connector/tap hardware

### When Starting Phase 4

- [ ] 12V→5V automotive DC-DC converter
- [ ] Fuse tap, wiring materials, heat shrink
- [ ] PETG filament for clamshell
- [ ] Standoffs and mounting hardware
