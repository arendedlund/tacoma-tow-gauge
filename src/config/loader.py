from __future__ import annotations

import json
import os
from typing import Any

from src.signals.decoder import (
    BroadcastDecoder,
    GaugeSignal,
    SignalDecoder,
    make_broadcast_decoder_from_config,
    make_decoder_from_config,
)


def load_config(
    config_dir: str,
) -> tuple[dict[str, GaugeSignal], list[SignalDecoder], list[BroadcastDecoder]]:
    """Load signals.json and thresholds.json; return instantiated signals and decoders.

    Signals with source "broadcast" get a BroadcastDecoder (passive listen, no request).
    Thresholds from thresholds.json override values in signals.json per-signal.
    """
    signals_path = os.path.join(config_dir, "signals.json")
    thresholds_path = os.path.join(config_dir, "thresholds.json")

    with open(signals_path) as f:
        signals_raw: list[dict[str, Any]] = json.load(f)
    with open(thresholds_path) as f:
        thresholds_raw: list[dict[str, Any]] = json.load(f)

    thresh_by_name = {t["signal_name"]: t for t in thresholds_raw}

    signals: dict[str, GaugeSignal] = {}
    decoders: list[SignalDecoder] = []
    broadcast_decoders: list[BroadcastDecoder] = []

    for entry in signals_raw:
        name = entry["name"]
        thresh = thresh_by_name.get(name, {})

        signal = GaugeSignal(
            name=name,
            label=entry["label"],
            unit=entry["unit"],
            threshold_warning=thresh.get("warning_celsius", entry.get("warning_threshold", 130.0)),
            threshold_critical=thresh.get("critical_celsius", entry.get("critical_threshold", 150.0)),
            staleness_timeout=thresh.get("staleness_timeout_s", entry.get("staleness_timeout_s", 10.0)),
            plausible_min=entry.get("plausible_min", -40.0),
            plausible_max=entry.get("plausible_max", 200.0),
        )
        signals[name] = signal

        if entry.get("source") == "broadcast":
            broadcast_decoders.append(make_broadcast_decoder_from_config(entry))
        else:
            decoders.append(make_decoder_from_config(entry))

    return signals, decoders, broadcast_decoders
