from __future__ import annotations

import json
import os
from typing import Any

from src.signals.decoder import GaugeSignal, SignalDecoder, make_decoder_from_config


def load_config(config_dir: str) -> tuple[dict[str, GaugeSignal], list[SignalDecoder]]:
    """Load signals.json and thresholds.json; return instantiated signals and decoders.

    Signals with status "pending-OQ-1" get a GaugeSignal (stays WAITING) but no decoder
    — no request will be sent for them until Phase 1 resolves the open question.

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

        if entry.get("status") == "pending-OQ-1":
            continue

        decoders.append(make_decoder_from_config(entry))

    return signals, decoders
