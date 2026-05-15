#!/usr/bin/env python3
"""Launcher — keeps the project root on sys.path so src/* imports resolve.

In windowed + virtual mode a CAN injector thread is started in-process so
the display shows live simulated signals. python-can's virtual bus is
process-local (in-memory queue), so the injector must share a process with
the reader — spawning a subprocess doesn't work.
"""

import sys
import os
import threading
import time


def _parse_bus_and_channel(argv: list[str]) -> tuple[str, str]:
    bus = "virtual"
    channel = "test"
    for i, arg in enumerate(argv):
        if arg == "--bus-interface" and i + 1 < len(argv):
            bus = argv[i + 1]
        elif arg == "--channel" and i + 1 < len(argv):
            channel = argv[i + 1]
    return bus, channel


def _start_injector_thread(channel: str) -> None:
    """Daemon thread that injects simulated CAN frames on the virtual bus.

    Runs a 30-second triangle-wave sweep from 0 °C through every warning and
    critical threshold and back, cycling continuously at 20 Hz so the display
    shows smooth, rapidly-changing values across all colour states.
    """
    import can
    from tools.inject_virtual_can import (
        _ATF_PIDS,
        _ATF_RESPONSE_HEADER,
        _ECT_FRAME_ID,
        _make_atf_response,
        _make_ect_frame,
    )

    # Peak temperatures — a few degrees above each signal's critical threshold
    _SWEEP_MAX   = {"atf": 158.0, "tc": 168.0, "ect": 128.0}
    _CYCLE_S     = 30.0   # seconds per full triangle-wave cycle
    _TICK_S      = 0.05   # 20 Hz update rate

    def _send(bus: "can.interface.Bus", temps: dict[str, float]) -> None:
        for name, pid in _ATF_PIDS.items():
            celsius = temps["atf"] if name == "atf" else temps["tc"]
            bus.send(can.Message(
                arbitration_id=_ATF_RESPONSE_HEADER,
                data=_make_atf_response(pid, celsius),
                is_extended_id=False,
            ))
        bus.send(can.Message(
            arbitration_id=_ECT_FRAME_ID,
            data=_make_ect_frame(temps["ect"]),
            is_extended_id=False,
        ))

    def _loop() -> None:
        bus = can.interface.Bus(channel=channel, interface="virtual")
        t0 = time.monotonic()
        try:
            while True:
                elapsed = time.monotonic() - t0
                # Triangle wave: phase 0→0.5 = rising, 0.5→1.0 = falling
                phase = (elapsed % _CYCLE_S) / _CYCLE_S
                frac  = (1.0 - abs(2.0 * phase - 1.0))  # 0→1→0
                temps = {k: v * frac for k, v in _SWEEP_MAX.items()}
                _send(bus, temps)
                time.sleep(_TICK_S)
        except Exception:
            pass
        finally:
            try:
                bus.shutdown()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="can-injector")
    t.start()
    print(
        f"[injector] sweep on virtual:{channel} — "
        f"30 s cycle, 20 Hz  "
        f"peaks: ECT {_SWEEP_MAX['ect']} °C  ATF {_SWEEP_MAX['atf']} °C  TC {_SWEEP_MAX['tc']} °C"
    )


def main() -> None:
    argv = sys.argv[1:]
    windowed = "--windowed" in argv
    bus, channel = _parse_bus_and_channel(argv)

    if windowed and bus == "virtual":
        _start_injector_thread(channel)

    from src.main import main as gauge_main
    gauge_main()


if __name__ == "__main__":
    main()
