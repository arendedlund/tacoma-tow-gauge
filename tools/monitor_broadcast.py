#!/usr/bin/env python3
"""Phase 1 tool: passively monitor Toyota broadcast frames using the opendbc DBC file.

Listens for:
  - 0x3BC (ECT1S92): BV_THOCL — ATF temperature broadcast candidate
  - 0x3C1 (ENG1S23): GATHW   — engine coolant temperature

Run this alongside capture_verify.py to cross-check Mode 22 PID values against
broadcast values in the same drive session.

Usage:
    python3 tools/monitor_broadcast.py [--dbc PATH] [--bus-interface {panda,socketcan}]

Default DBC: ~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc
"""

import argparse
import os
import sys
import time

_FRAMES_OF_INTEREST = {
    0x3BC: "ECT1S92",  # BV_THOCL — ATF temp candidate (see research.md §2a)
    0x3C1: "ENG1S23",  # GATHW    — coolant temp contingency for Slot 1
}


def main() -> None:
    default_dbc = os.path.expanduser(
        "~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dbc", default=default_dbc, help="Path to Toyota DBC file")
    parser.add_argument(
        "--bus-interface",
        choices=["panda", "socketcan"],
        default="panda",
        help="CAN source (default: panda)",
    )
    args = parser.parse_args()

    db = None
    try:
        import cantools  # type: ignore[import]
        if os.path.exists(args.dbc):
            try:
                db = cantools.database.load_file(args.dbc, strict=False)
            except Exception as exc:
                print(f"[warn] cantools could not parse DBC ({exc}); using built-in decoders.")
                print("       Install cantools>=39.4 in a venv for full DBC support.\n")
        else:
            print(f"[warn] DBC not found: {args.dbc}; using built-in decoders.\n")
    except ImportError:
        print("[warn] cantools not installed; using built-in decoders.\n")
    print(f"Loaded DBC: {args.dbc}")
    print("Monitoring frames:")
    for fid, name in _FRAMES_OF_INTEREST.items():
        print(f"  0x{fid:03X}  {name}")
    print("Press Ctrl-C to stop.\n")

    col = f"{'Time':>8}  {'ID':>6}  {'Message':<12}  {'Signal':<18}  {'Value':>12}"
    print(col)
    print("-" * len(col))

    def _fallback_decode(arb_id: int, data: bytes) -> list[tuple[str, float, str]]:
        """Built-in decoders for the two frames we care about (no DBC required)."""
        results = []
        if arb_id == 0x3BC and len(data) >= 5:
            # BV_THOCL: bits 23|16 big-endian unsigned, scale 0.625, offset -50
            raw = (data[2] << 8) | data[3]
            results.append(("BV_THOCL", raw * 0.625 - 50, "°C (ATF candidate)"))
        if arb_id == 0x3C1 and len(data) >= 3:
            # GATHW: bits 15|16 big-endian signed, scale 0.625, offset 0
            raw = (data[0] << 8) | data[1]
            if raw & 0x8000:
                raw -= 0x10000
            results.append(("GATHW", raw * 0.625, "°C (coolant)"))
        return results

    def process(arb_id: int, data: bytes) -> None:
        if arb_id not in _FRAMES_OF_INTEREST:
            return
        ts = time.strftime("%H:%M:%S")
        msg_name = _FRAMES_OF_INTEREST[arb_id]
        data = bytes(data)

        if db is not None:
            try:
                msg = db.get_message_by_frame_id(arb_id)
                decoded = msg.decode(data, decode_choices=False)
                for sig_name, value in decoded.items():
                    unit = ""
                    try:
                        sig = msg.get_signal_by_name(sig_name)
                        unit = sig.unit or ""
                    except Exception:
                        pass
                    print(
                        f"{ts:>8}  0x{arb_id:03X}  {msg_name:<12}"
                        f"  {sig_name:<18}  {value:>10.3f} {unit}"
                    )
                return
            except Exception:
                pass

        for sig_name, value, unit in _fallback_decode(arb_id, data):
            print(
                f"{ts:>8}  0x{arb_id:03X}  {msg_name:<12}"
                f"  {sig_name:<18}  {value:>10.3f} {unit}"
            )

    if args.bus_interface == "panda":
        try:
            from panda import Panda  # type: ignore[import]
        except ImportError:
            print("ERROR: panda library not installed.")
            sys.exit(1)
        p = Panda()
        p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
        while True:
            for msg in p.can_recv():
                process(msg[0], msg[2])
    else:
        import can  # type: ignore[import]
        bus = can.interface.Bus("can0", interface="socketcan")
        try:
            while True:
                msg = bus.recv(timeout=1.0)
                if msg:
                    process(msg.arbitration_id, msg.data)
        finally:
            bus.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
