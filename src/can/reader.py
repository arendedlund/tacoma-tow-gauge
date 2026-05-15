from __future__ import annotations

import threading
import time
from typing import Optional

from src.signals.decoder import BroadcastDecoder, GaugeSignal, SignalDecoder

_POLL_INTERVAL_S = 1.0       # seconds between OBD-II request cycles
_STALE_TICK_INTERVAL_S = 0.5 # seconds between staleness ticks


class CANReader:
    """Background thread that reads CAN frames and updates GaugeSignal state.

    Supports three bus interfaces selected at construction time:
      "panda"     — uses the comma.ai panda library (Phase 2)
      "virtual"   — uses python-can virtual bus (local development)
      "socketcan" — uses python-can SocketCAN / MCP2515 (Phase 3+)

    The signal decoding and GaugeSignal update logic is identical across all
    interfaces; only the frame source changes.
    """

    def __init__(
        self,
        signals: dict[str, GaugeSignal],
        decoders: list[SignalDecoder],
        broadcast_decoders: list[BroadcastDecoder] | None = None,
        bus_interface: str = "virtual",
        channel: str = "test",
    ) -> None:
        self.signals = signals
        self.decoders = decoders
        self.broadcast_decoders = broadcast_decoders or []
        self.bus_interface = bus_interface
        self.channel = channel
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="can-reader"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        if self.bus_interface == "panda":
            self._run_panda()
        else:
            self._run_python_can()

    # ------------------------------------------------------------------
    # panda interface (Phase 2)
    # ------------------------------------------------------------------

    def _run_panda(self) -> None:
        from panda import Panda  # type: ignore[import]

        p = Panda()
        p.set_safety_mode(Panda.SAFETY_ALLOUTPUT)
        last_poll = 0.0
        last_tick = 0.0

        while self._running:
            now = time.monotonic()

            if now - last_poll >= _POLL_INTERVAL_S:
                for decoder in self.decoders:
                    p.can_send(decoder.request_header, decoder.request_bytes(), 0)
                last_poll = now

            for msg in p.can_recv():
                self._dispatch(msg[0], bytes(msg[2]))

            if now - last_tick >= _STALE_TICK_INTERVAL_S:
                self._tick_all()
                last_tick = now

            time.sleep(0.01)

    # ------------------------------------------------------------------
    # python-can interface (virtual + socketcan, Phase 3+)
    # ------------------------------------------------------------------

    def _run_python_can(self) -> None:
        import can  # type: ignore[import]

        if self.bus_interface == "virtual":
            bus = can.interface.Bus(channel=self.channel, interface="virtual")
        else:
            bus = can.interface.Bus(channel="can0", interface="socketcan")

        last_poll = 0.0
        last_tick = 0.0

        try:
            while self._running:
                now = time.monotonic()

                if now - last_poll >= _POLL_INTERVAL_S:
                    for decoder in self.decoders:
                        msg = can.Message(
                            arbitration_id=decoder.request_header,
                            data=decoder.request_bytes(),
                            is_extended_id=False,
                        )
                        try:
                            bus.send(msg)
                        except Exception:
                            pass
                    last_poll = now

                msg = bus.recv(timeout=0.05)
                if msg is not None:
                    self._dispatch(msg.arbitration_id, bytes(msg.data))

                if now - last_tick >= _STALE_TICK_INTERVAL_S:
                    self._tick_all()
                    last_tick = now
        finally:
            bus.shutdown()

    # ------------------------------------------------------------------
    # Shared dispatch + staleness tick
    # ------------------------------------------------------------------

    def _dispatch(self, arb_id: int, data: bytes) -> None:
        for decoder in self.decoders:
            if decoder.matches(arb_id, data):
                try:
                    value = decoder.decode(data)
                    signal = self.signals.get(decoder.signal_name)
                    if signal is not None:
                        signal.on_receive_frame(value)
                except Exception:
                    pass
        for decoder in self.broadcast_decoders:
            if decoder.matches(arb_id):
                try:
                    value = decoder.decode(data)
                    signal = self.signals.get(decoder.signal_name)
                    if signal is not None:
                        signal.on_receive_frame(value)
                except Exception:
                    pass

    def _tick_all(self) -> None:
        for signal in self.signals.values():
            signal.on_tick()
