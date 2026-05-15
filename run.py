#!/usr/bin/env python3
"""Launcher — keeps the project root on sys.path so src/* imports resolve.

In windowed + virtual mode the CAN injector is started automatically so
the display shows live simulated signals without a separate terminal.
"""

import subprocess
import sys
import os


def _parse_bus_and_channel(argv: list[str]) -> tuple[str, str]:
    bus = "virtual"
    channel = "test"
    for i, arg in enumerate(argv):
        if arg == "--bus-interface" and i + 1 < len(argv):
            bus = argv[i + 1]
        elif arg == "--channel" and i + 1 < len(argv):
            channel = argv[i + 1]
    return bus, channel


def main() -> None:
    argv = sys.argv[1:]
    windowed = "--windowed" in argv
    bus, channel = _parse_bus_and_channel(argv)

    injector: subprocess.Popen | None = None
    if windowed and bus == "virtual":
        injector_cmd = [
            sys.executable,
            os.path.join(os.path.dirname(__file__), "tools", "inject_virtual_can.py"),
            "--channel", channel,
        ]
        injector = subprocess.Popen(injector_cmd)

    try:
        from src.main import main as gauge_main
        gauge_main()
    finally:
        if injector is not None:
            injector.terminate()
            injector.wait()


if __name__ == "__main__":
    main()
