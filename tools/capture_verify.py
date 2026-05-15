#!/usr/bin/env python3
"""Phase 1 tool: query ATF pan and TC outlet temps via panda and print decoded values.

Sends Mode 22 requests every second to the TCM (header 0x7E1), listens for responses
on 0x7E9, and prints decoded °C values to stdout. Run this in the vehicle with the
panda connected to the OBD-II port.

Usage:
    python3 tools/capture_verify.py

Requires: pip install 'git+https://github.com/commaai/panda.git'
"""

import sys
import time

_REQUEST_HEADER = 0x7E1
_RESPONSE_HEADER = 0x7E9
_OBD_MODE = 0x22

_SIGNALS = [
    {"name": "ATF Pan Temp  (PID 0x1627)", "pid": 0x1627, "warn": 130.0, "crit": 150.0},
    {"name": "TC Outlet Temp (PID 0x1628)", "pid": 0x1628, "warn": 140.0, "crit": 160.0},
]


def _decode_atf(data: bytes) -> float:
    """ATF/TC decode: (A*459/255 + B*1.6/255 - 40) °F → °C."""
    A = data[3]
    B = data[4]
    temp_f = (A * 459 / 255) + (B * 1.6 / 255) - 40
    return (temp_f - 32) * 5 / 9


def _response_matches(data: bytes, pid: int) -> bool:
    if len(data) < 5:
        return False
    return (
        data[0] == 0x62
        and data[1] == (pid >> 8) & 0xFF
        and data[2] == pid & 0xFF
    )


def _state_label(temp: float, warn: float, crit: float) -> str:
    if temp >= crit:
        return "CRITICAL"
    if temp >= warn:
        return "WARNING"
    return "OK"


def main() -> None:
    try:
        from panda import Panda  # type: ignore[import]
    except ImportError:
        print("ERROR: panda library not installed.")
        print("  pip install 'git+https://github.com/commaai/panda.git'")
        sys.exit(1)

    print("Connecting to panda...")
    p = Panda()
    p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
    print("Connected. Polling every 1 s — Ctrl-C to stop.\n")

    header = f"{'Time':>8}  {'Signal':<28}  {'Raw bytes':>18}  {'°C':>8}  State"
    print(header)
    print("-" * len(header))

    while True:
        for sig in _SIGNALS:
            pid = sig["pid"]
            pid_high = (pid >> 8) & 0xFF
            pid_low = pid & 0xFF
            p.can_send(
                _REQUEST_HEADER,
                bytes([0x03, _OBD_MODE, pid_high, pid_low, 0, 0, 0, 0]),
                0,
            )

        time.sleep(0.15)

        msgs = p.can_recv()
        ts = time.strftime("%H:%M:%S")
        for msg in msgs:
            arb_id, _, data, _bus = msg
            if arb_id != _RESPONSE_HEADER:
                continue
            for sig in _SIGNALS:
                if _response_matches(bytes(data), sig["pid"]):
                    temp = _decode_atf(bytes(data))
                    state = _state_label(temp, sig["warn"], sig["crit"])
                    print(
                        f"{ts:>8}  {sig['name']:<28}  {bytes(data).hex():>18}"
                        f"  {temp:>7.1f}°C  {state}"
                    )

        time.sleep(0.85)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
