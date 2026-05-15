#!/usr/bin/env python3
"""Inject synthetic Mode 22 response frames onto a python-can virtual bus.

Simulates ATF pan temp and TC outlet temp so the gauge app can be exercised
on macOS without any hardware. Run this in one terminal and the gauge in another.

Usage:
    python3 tools/inject_virtual_can.py [--atf CELSIUS] [--tc CELSIUS]
    python3 tools/inject_virtual_can.py --atf 145 --tc 155   # trigger warnings/critical

In a separate terminal:
    python3 src/main.py --config config/ --windowed --bus-interface virtual
"""

import argparse
import time

import can

_RESPONSE_HEADER = 0x7E9
_OBD_MODE_RESP = 0x62  # 0x40 | 0x22

_PIDS = {
    "atf": 0x1627,
    "tc":  0x1628,
}


def _celsius_to_ab(celsius: float) -> tuple[int, int]:
    """Reverse the ATF decode formula to find byte values A, B for a target °C."""
    temp_f = celsius * 9 / 5 + 32
    target = temp_f + 40  # = A*459/255 + B*1.6/255
    A = min(255, max(0, round(target * 255 / 459)))
    remainder = target - A * 459 / 255
    B = min(255, max(0, round(remainder * 255 / 1.6)))
    return A, B


def _make_response(pid: int, celsius: float) -> bytes:
    pid_high = (pid >> 8) & 0xFF
    pid_low  = pid & 0xFF
    A, B = _celsius_to_ab(celsius)
    return bytes([_OBD_MODE_RESP, pid_high, pid_low, A, B, 0x00, 0x00, 0x00])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--atf",     type=float, default=95.0,  help="ATF pan temp °C (default: 95)")
    parser.add_argument("--tc",      type=float, default=105.0, help="TC outlet temp °C (default: 105)")
    parser.add_argument("--channel", default="test",            help="Virtual bus channel (default: test)")
    args = parser.parse_args()

    bus = can.interface.Bus(channel=args.channel, interface="virtual")
    print(f"Injecting on virtual:{args.channel}  ATF={args.atf}°C  TC={args.tc}°C")
    print("Ctrl-C to stop\n")

    # Sanity-check round-trip
    for name, pid in _PIDS.items():
        celsius = args.atf if name == "atf" else args.tc
        A, B = _celsius_to_ab(celsius)
        roundtrip = ((A * 459 / 255) + (B * 1.6 / 255) - 40 - 32) * 5 / 9
        print(f"  {name}: target={celsius:.1f}°C  A={A} B={B}  decoded={roundtrip:.1f}°C")
    print()

    try:
        while True:
            for name, pid in _PIDS.items():
                celsius = args.atf if name == "atf" else args.tc
                data = _make_response(pid, celsius)
                msg = can.Message(
                    arbitration_id=_RESPONSE_HEADER,
                    data=data,
                    is_extended_id=False,
                )
                bus.send(msg)
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        bus.shutdown()


if __name__ == "__main__":
    main()
