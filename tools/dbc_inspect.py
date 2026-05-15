#!/usr/bin/env python3
"""CLI: inspect a Toyota DBC file — list signals for a frame ID, or dump all messages.

Usage:
    python3 tools/dbc_inspect.py --frame-id 0x3BC
    python3 tools/dbc_inspect.py --all
    python3 tools/dbc_inspect.py --frame-id 0x3BC --decode AABBCCDDEEFF0011

Default DBC: ~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc
"""

import argparse
import os
import sys


def main() -> None:
    default_dbc = os.path.expanduser(
        "~/Development/opendbc/opendbc/dbc/toyota_2017_ref_pt.dbc"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dbc", default=default_dbc, help="Path to DBC file")
    parser.add_argument("--frame-id", help="Hex frame ID to inspect, e.g. 0x3BC")
    parser.add_argument("--all", action="store_true", help="List all messages")
    parser.add_argument(
        "--decode",
        help="Hex payload to decode for the given --frame-id, e.g. 0000F00000000000",
    )
    args = parser.parse_args()

    try:
        import cantools  # type: ignore[import]
    except ImportError:
        print("ERROR: cantools not installed — run: pip install cantools")
        sys.exit(1)

    if not os.path.exists(args.dbc):
        print(f"ERROR: DBC not found: {args.dbc}")
        sys.exit(1)

    try:
        db = cantools.database.load_file(args.dbc, strict=False)
    except Exception as exc:
        print(f"ERROR: could not parse DBC: {exc}")
        print("The DBC contains extended-frame IDs that require cantools>=39.4.")
        print("Set up a venv and run: pip install 'cantools>=39.4.0'")
        sys.exit(1)

    if args.all:
        for msg in sorted(db.messages, key=lambda m: m.frame_id):
            print(f"0x{msg.frame_id:03X}  {msg.name}  ({msg.length} bytes)")
            for sig in msg.signals:
                print(
                    f"  {sig.name:<22} bits={sig.start}|{sig.length}"
                    f"  scale={sig.scale}  offset={sig.offset}"
                    f"  unit={sig.unit!r}"
                )
        return

    if args.frame_id:
        frame_id = int(args.frame_id, 16)
        try:
            msg = db.get_message_by_frame_id(frame_id)
        except KeyError:
            print(f"Frame ID 0x{frame_id:03X} not found in DBC.")
            sys.exit(1)

        print(f"Message : {msg.name}")
        print(f"ID      : 0x{msg.frame_id:03X}  ({msg.frame_id} dec)")
        print(f"Length  : {msg.length} bytes")
        print(f"{'Signal':<22} {'bits':>8}  {'scale':>10}  {'offset':>10}  unit")
        print("-" * 65)
        for sig in msg.signals:
            print(
                f"{sig.name:<22} {sig.start}|{sig.length:>3}"
                f"  {sig.scale:>10}  {sig.offset:>10}  {sig.unit!r}"
            )

        if args.decode:
            raw = bytes.fromhex(args.decode.replace(" ", ""))
            print(f"\nDecoded 0x{args.decode}:")
            decoded = msg.decode(raw, decode_choices=False)
            for sig_name, value in decoded.items():
                print(f"  {sig_name:<22} = {value}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
