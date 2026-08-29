"""Shared helpers for the validation suite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

D01 = DATA / "01_blink_jaw_devices" / "30162868"
D01_SOURCE = D01 / "sourcedata"
D02 = DATA / "02_ds002718_bids_eog"
D03 = DATA / "03_incog_clean_vs_noisy" / (
    "iNCog-EEG (ideal vs. Noisy Cognitive EEG for Workload_Assessment) Dataset"
)
D04 = DATA / "04_semisim_eog"

# Dataset 01 device codes -> how we describe them.
DEVICES = {
    "DSI": {"label": "DSI-24", "tier": "research", "channels": 24, "price_tier": "$$$$"},
    "Muse2": {"label": "Muse 2", "tier": "consumer", "channels": 4, "price_tier": "$"},
    "MW2": {"label": "MindWave 2", "tier": "consumer", "channels": 1, "price_tier": "$"},
    "BLP": {"label": "BrainLink Pro", "tier": "consumer", "channels": 1, "price_tier": "$"},
}

TASKS = {
    "EB": "eye blink",
    "BT": "jaw clench",
    "MVO": "head movement (eyes open)",
    "MVC": "head movement (eyes closed)",
}

# The cued beep marker in dataset 01's EDF annotations.
BEEP_SUFFIX = "Number_02"

# Response latency after the cue. The beep is an instruction, not a measured
# onset, so a detection is credited if it lands inside this window.
RESPONSE_WINDOW = (-0.3, 2.0)


@dataclass
class Segments:
    """The three phases of a dataset 01 recording, in seconds."""

    rest_pre: tuple[float, float]
    task: tuple[float, float]
    rest_post: tuple[float, float]
    beeps: list[float]


def subject_dirs(base: Path, pattern: str = "sub-*") -> list[Path]:
    return sorted(p for p in base.glob(pattern) if p.is_dir())


def beep_times(rec) -> list[float]:
    """Cued artifact times from a dataset 01 recording's EDF annotations."""
    return [
        a.onset
        for a in rec.meta.get("annotations", [])
        if a.description.endswith(BEEP_SUFFIX)
    ]


def segments(rec) -> Segments | None:
    """Split a dataset 01 recording into rest / task / rest.

    Returns ``None`` when the expected 20 cues are not present, so callers skip
    the file rather than silently scoring a malformed one.
    """
    beeps = beep_times(rec)
    if len(beeps) != 20:
        return None

    first, last = beeps[0], beeps[-1]
    # Guard bands keep the response to the last cue out of the rest window.
    return Segments(
        rest_pre=(0.0, max(0.0, first - 3.0)),
        task=(first - 1.0, last + 3.0),
        rest_post=(min(rec.duration, last + 5.0), rec.duration),
        beeps=beeps,
    )


def match_events(
    detected: list[float],
    cues: list[float],
    window: tuple[float, float] = RESPONSE_WINDOW,
) -> tuple[int, int, int]:
    """Greedily match detections to cues.

    Returns ``(n_matched_cues, n_detections_in_windows, n_detections_outside)``.

    Precision against cues is deliberately *not* computed as
    ``matched / detected``: subjects blink spontaneously between cues, so a
    detection outside a cue window is frequently a real blink rather than a
    false positive. What is measurable without frame-by-frame video annotation
    is recall, and detections-per-cue as a calibration target.
    """
    lo, hi = window
    used: set[int] = set()
    matched = 0
    for cue in cues:
        for i, t in enumerate(detected):
            if i in used:
                continue
            if cue + lo <= t <= cue + hi:
                used.add(i)
                matched += 1
                break
    inside = sum(
        1 for t in detected if any(c + lo <= t <= c + hi for c in cues)
    )
    return matched, inside, len(detected) - inside


def summarise(values: list[float]) -> dict:
    """Mean, SD, n and a 95% CI, or nulls when there is nothing to report."""
    arr = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return {"n": 0, "mean": None, "sd": None, "ci95": None}
    mean = float(arr.mean())
    sd = float(arr.std(ddof=1)) if arr.size > 1 else 0.0
    half = 1.96 * sd / np.sqrt(arr.size) if arr.size > 1 else 0.0
    return {
        "n": int(arr.size),
        "mean": round(mean, 4),
        "sd": round(sd, 4),
        "ci95": [round(mean - half, 4), round(mean + half, 4)],
    }


def auc(positive: list[float], negative: list[float]) -> float | None:
    """Probability a random positive scores above a random negative."""
    if not positive or not negative:
        return None
    p = np.asarray(positive)[:, None]
    n = np.asarray(negative)[None, :]
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def cohens_d(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(b) < 2:
        return None
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt((va + vb) / 2)
    if pooled == 0:
        return None
    return float((np.mean(a) - np.mean(b)) / pooled)
