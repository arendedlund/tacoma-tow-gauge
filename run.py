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
    """Daemon thread that continuously injects fake CAN frames on the virtual bus."""
    import can
    from tools.inject_virtual_can import (
        _ATF_PIDS,
        _ATF_RESPONSE_HEADER,
        _ECT_FRAME_ID,
        _make_atf_response,
        _make_ect_frame,
    )

    _DEFAULTS = {"atf": 95.0, "tc": 105.0, "ect": 90.0}

    def _loop() -> None:
        bus = can.interface.Bus(channel=channel, interface="virtual")
        try:
            while True:
                for name, pid in _ATF_PIDS.items():
                    celsius = _DEFAULTS["atf"] if name == "atf" else _DEFAULTS["tc"]
                    bus.send(can.Message(
                        arbitration_id=_ATF_RESPONSE_HEADER,
                        data=_make_atf_response(pid, celsius),
                        is_extended_id=False,
                    ))
                bus.send(can.Message(
                    arbitration_id=_ECT_FRAME_ID,
                    data=_make_ect_frame(_DEFAULTS["ect"]),
                    is_extended_id=False,
                ))
                time.sleep(1.0)
        except Exception:
            pass
        finally:
            try:
                bus.shutdown()
            except Exception:
                pass

    t = threading.Thread(target=_loop, daemon=True, name="can-injector")
    t.start()
    print(f"[injector] started on virtual:{channel} "
          f"ATF={_DEFAULTS['atf']}°C  TC={_DEFAULTS['tc']}°C  ECT={_DEFAULTS['ect']}°C")


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
