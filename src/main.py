#!/usr/bin/env python3
"""Tacoma Tow Gauge — entry point.

Usage (local dev, no hardware):
    python3 src/main.py --config config/ --windowed --bus-interface virtual

Usage (vehicle, Phase 2 with panda):
    python3 src/main.py --config config/ --bus-interface panda

Usage (vehicle, Phase 3+ with MCP2515/SocketCAN):
    python3 src/main.py --config config/ --bus-interface socketcan
"""

import argparse
import signal
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Tacoma tow gauge display")
    parser.add_argument("--config", default="config/", help="Path to config directory")
    parser.add_argument(
        "--windowed", action="store_true", help="Windowed mode for macOS dev"
    )
    parser.add_argument(
        "--bus-interface",
        choices=["panda", "virtual", "socketcan"],
        default="virtual",
        help="CAN bus source (default: virtual)",
    )
    parser.add_argument(
        "--channel",
        default="test",
        help="python-can channel name for virtual bus (default: test)",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help=(
            "Window scale factor for windowed mode (default: 1.0). "
            "Use ~0.5 on a 2× Retina Mac to approximate the physical "
            "7-inch Microtips display size."
        ),
    )
    args = parser.parse_args()

    from src.can.reader import CANReader
    from src.config.loader import load_config
    from src.display.renderer import Renderer

    signals, decoders, broadcast_decoders = load_config(args.config)

    reader = CANReader(
        signals=signals,
        decoders=decoders,
        broadcast_decoders=broadcast_decoders,
        bus_interface=args.bus_interface,
        channel=args.channel,
    )

    renderer = Renderer(signals=signals, windowed=args.windowed, scale=args.scale)
    renderer.setup()

    reader.start()

    def _shutdown(signum: int, frame: object) -> None:
        reader.stop()
        renderer.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)

    try:
        renderer.run()
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()
        renderer.stop()


if __name__ == "__main__":
    main()
