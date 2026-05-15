from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Callable, Optional


class SignalState(Enum):
    WAITING = "WAITING"      # No frame received since power-on
    NORMAL = "NORMAL"        # Value within normal operating range
    WARNING = "WARNING"      # Value >= warning threshold
    CRITICAL = "CRITICAL"    # Value >= critical threshold
    NO_SIGNAL = "NO_SIGNAL"  # No valid frame within staleness_timeout
    FAULT = "FAULT"          # Decoded value outside plausible range


@dataclass
class GaugeSignal:
    name: str
    label: str
    unit: str
    threshold_warning: float
    threshold_critical: float
    staleness_timeout: float
    plausible_min: float
    plausible_max: float

    value: Optional[float] = field(default=None, init=False)
    state: SignalState = field(default=SignalState.WAITING, init=False)
    last_updated: Optional[float] = field(default=None, init=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False, compare=False)

    def on_receive_frame(self, decoded_value: float) -> None:
        with self._lock:
            if decoded_value < self.plausible_min or decoded_value > self.plausible_max:
                self.state = SignalState.FAULT
            elif decoded_value >= self.threshold_critical:
                self.state = SignalState.CRITICAL
            elif decoded_value >= self.threshold_warning:
                self.state = SignalState.WARNING
            else:
                self.state = SignalState.NORMAL
            self.value = decoded_value
            self.last_updated = time.monotonic()

    def on_tick(self) -> None:
        with self._lock:
            if self.last_updated is None:
                self.state = SignalState.WAITING
            elif time.monotonic() - self.last_updated > self.staleness_timeout:
                self.state = SignalState.NO_SIGNAL

    def snapshot(self) -> tuple[Optional[float], SignalState]:
        """Return a consistent (value, state) pair under lock for the render thread."""
        with self._lock:
            return self.value, self.state


@dataclass
class SignalDecoder:
    """Knows how to match and decode one OBD-II Mode 22 request/response pair."""

    signal_name: str
    request_header: int   # Arbitration ID to send the request to
    response_header: int  # Arbitration ID of the expected response
    obd_mode: int         # e.g. 0x22
    obd_pid: int          # e.g. 0x1627
    decode_fn: Callable[[bytes], float]

    def request_bytes(self) -> bytes:
        """Build the 8-byte OBD-II Mode 22 request frame."""
        pid_high = (self.obd_pid >> 8) & 0xFF
        pid_low = self.obd_pid & 0xFF
        return bytes([0x03, self.obd_mode, pid_high, pid_low, 0x00, 0x00, 0x00, 0x00])

    def matches(self, arbitration_id: int, data: bytes) -> bool:
        """Return True if this frame is the response for our PID."""
        if arbitration_id != self.response_header:
            return False
        if len(data) < 3:
            return False
        response_mode = 0x40 | self.obd_mode
        if data[0] != response_mode:
            return False
        pid_high = (self.obd_pid >> 8) & 0xFF
        pid_low = self.obd_pid & 0xFF
        return data[1] == pid_high and data[2] == pid_low

    def decode(self, data: bytes) -> float:
        return self.decode_fn(data)


def _make_formula_decoder(formula: str, variables: dict) -> Callable[[bytes], float]:
    """Build a decode function from a formula string and variable byte-position map.

    The formula is a Python expression evaluated with each variable substituted from
    the response payload. Only the named variables are in scope — no builtins.
    This is safe because signals.json is a trusted local config file, not user input.
    """
    def decode_fn(data: bytes) -> float:
        env: dict[str, float] = {}
        for var_name, spec in variables.items():
            idx = spec["byte_index"]
            count = spec.get("byte_count", 1)
            if count == 1:
                env[var_name] = float(data[idx])
            else:
                val = 0
                for i in range(count):
                    val = (val << 8) | data[idx + i]
                env[var_name] = float(val)
        return float(eval(formula, {"__builtins__": {}}, env))  # noqa: S307

    return decode_fn


def make_decoder_from_config(entry: dict) -> SignalDecoder:
    """Construct a SignalDecoder from a signals.json entry."""
    decode_cfg = entry["decode"]
    decode_fn = _make_formula_decoder(decode_cfg["formula"], decode_cfg["variables"])
    return SignalDecoder(
        signal_name=entry["name"],
        request_header=int(entry["request_header"], 16),
        response_header=int(entry["response_header"], 16),
        obd_mode=int(entry["obd_mode"], 16),
        obd_pid=int(entry["obd_pid"], 16),
        decode_fn=decode_fn,
    )


@dataclass
class BroadcastDecoder:
    """Decodes a passively-received broadcast CAN frame (no request/response cycle)."""

    signal_name: str
    frame_id: int
    decode_fn: Callable[[bytes], float]

    def matches(self, arbitration_id: int) -> bool:
        return arbitration_id == self.frame_id

    def decode(self, data: bytes) -> float:
        return self.decode_fn(data)


def make_broadcast_decoder_from_config(entry: dict) -> BroadcastDecoder:
    """Construct a BroadcastDecoder from a signals.json broadcast entry."""
    decode_cfg = entry["decode"]
    decode_fn = _make_formula_decoder(decode_cfg["formula"], decode_cfg["variables"])
    return BroadcastDecoder(
        signal_name=entry["name"],
        frame_id=int(entry["frame_id"], 16),
        decode_fn=decode_fn,
    )
