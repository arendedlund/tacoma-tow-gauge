#!/usr/bin/env python3
"""Inject synthetic CAN frames onto a python-can virtual bus.

Simulates all three gauge signals so the display can be exercised on macOS
without any hardware. Automatically started by run.py in windowed+virtual mode,
or run manually in a separate terminal.

Usage:
    python3 tools/inject_virtual_can.py [--atf C] [--tc C] [--ect C]
    python3 tools/inject_virtual_can.py --atf 145 --tc 155 --ect 108
"""

import argparse
import time

import can

# Mode 22 response frames (ATF pan + TC outlet) → 0x7E9
_ATF_RESPONSE_HEADER = 0x7E9
_OBD_MODE_RESP = 0x62  # 0x40 | 0x22

_ATF_PIDS = {
    "atf": 0x1627,
    "tc":  0x1628,
}

# GATHW broadcast frame (ECT / coolant temp) → 0x3C1
_ECT_FRAME_ID = 0x3C1


def _celsius_to_ab(celsius: float) -> tuple[int, int]:
    """Reverse the ATF decode formula to produce byte values A, B for a target °C."""
    temp_f = celsius * 9 / 5 + 32
    target = temp_f + 40
    A = min(255, max(0, round(target * 255 / 459)))
    remainder = target - A * 459 / 255
    B = min(255, max(0, round(remainder * 255 / 1.6)))
    return A, B


def _make_atf_response(pid: int, celsius: float) -> bytes:
    pid_high = (pid >> 8) & 0xFF
    pid_low  = pid & 0xFF
    A, B = _celsius_to_ab(celsius)
    return bytes([_OBD_MODE_RESP, pid_high, pid_low, A, B, 0x00, 0x00, 0x00])


def _make_ect_frame(celsius: float) -> bytes:
    """Encode coolant temp as GATHW: raw = round(C / 0.625), big-endian bytes 0-1."""
    raw = max(0, min(0xFFFF, round(celsius / 0.625)))
    hi = (raw >> 8) & 0xFF
    lo = raw & 0xFF
    return bytes([hi, lo, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atf",     type=float, default=95.0,  help="ATF pan temp °C (default: 95)")
    parser.add_argument("--tc",      type=float, default=105.0, help="TC outlet temp °C (default: 105)")
    parser.add_argument("--ect",     type=float, default=90.0,  help="Engine coolant temp °C (default: 90)")
    parser.add_argument("--channel", default="test",            help="Virtual bus channel (default: test)")
    args = parser.parse_args()

    bus = can.interface.Bus(channel=args.channel, interface="virtual")
    print(f"Injecting on virtual:{args.channel}  ATF={args.atf}°C  TC={args.tc}°C  ECT={args.ect}°C")
    print("Ctrl-C to stop\n")

    # Round-trip check for ATF signals
    for name, pid in _ATF_PIDS.items():
        celsius = args.atf if name == "atf" else args.tc
        A, B = _celsius_to_ab(celsius)
        rt = ((A * 459 / 255) + (B * 1.6 / 255) - 40 - 32) * 5 / 9
        print(f"  {name}: target={celsius:.1f}°C  A={A} B={B}  decoded={rt:.1f}°C")
    ect_raw = round(args.ect / 0.625)
    print(f"  ect: target={args.ect:.1f}°C  raw={ect_raw}  decoded={ect_raw * 0.625:.1f}°C")
    print()

    try:
        while True:
            for name, pid in _ATF_PIDS.items():
                celsius = args.atf if name == "atf" else args.tc
                bus.send(can.Message(
                    arbitration_id=_ATF_RESPONSE_HEADER,
                    data=_make_atf_response(pid, celsius),
                    is_extended_id=False,
                ))
            bus.send(can.Message(
                arbitration_id=_ECT_FRAME_ID,
                data=_make_ect_frame(args.ect),
                is_extended_id=False,
            ))
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
