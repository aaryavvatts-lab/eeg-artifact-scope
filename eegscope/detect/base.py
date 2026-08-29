"""Shared vocabulary for detectors.

Every detector returns the same shape of answer so scoring, the report and the
UI never special-case an artifact type.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# Artifact classes the tool knows about.
BLINK = "blink"
MUSCLE = "muscle"
CARDIAC = "cardiac"
LINE_NOISE = "line_noise"
DRIFT = "drift"
POP = "electrode_pop"

HUMAN_LABEL = {
    BLINK: "Eye blink",
    MUSCLE: "Muscle / jaw clench",
    CARDIAC: "Heartbeat",
    LINE_NOISE: "Mains line noise",
    DRIFT: "Drift / movement",
    POP: "Electrode pop",
}


@dataclass
class ArtifactEvent:
    """One detected artifact occurrence."""

    onset: float           # seconds from recording start
    duration: float        # seconds
    kind: str              # one of the constants above
    severity: float        # 0-1, how far past threshold this was
    channels: list[str] = field(default_factory=list)  # empty = whole-head

    @property
    def offset(self) -> float:
        return self.onset + self.duration

    def as_dict(self) -> dict:
        return {
            "onset": round(self.onset, 4),
            "duration": round(self.duration, 4),
            "kind": self.kind,
            "severity": round(self.severity, 4),
            "channels": self.channels,
        }


@dataclass
class DetectorResult:
    """What a detector found, plus enough context to explain it."""

    kind: str
    events: list[ArtifactEvent] = field(default_factory=list)
    per_channel: dict[str, float] = field(default_factory=dict)
    threshold: float | None = None
    detail: dict = field(default_factory=dict)
    # Set when the detector could not run (e.g. sample rate too low). A skipped
    # detector must never be scored as "clean" -- that would reward bad files.
    skipped_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.skipped_reason is None

    @property
    def n_events(self) -> int:
        return len(self.events)

    def contaminated_seconds(self) -> float:
        """Total time covered by events, counting overlaps once."""
        if not self.events:
            return 0.0
        spans = sorted((e.onset, e.offset) for e in self.events)
        total = 0.0
        cur_start, cur_end = spans[0]
        for s, e in spans[1:]:
            if s > cur_end:
                total += cur_end - cur_start
                cur_start, cur_end = s, e
            else:
                cur_end = max(cur_end, e)
        return total + (cur_end - cur_start)

    def rate_per_minute(self, duration: float) -> float:
        return self.n_events / (duration / 60.0) if duration > 0 else 0.0

    def as_dict(self, duration: float | None = None) -> dict:
        out = {
            "kind": self.kind,
            "label": HUMAN_LABEL.get(self.kind, self.kind),
            "n_events": self.n_events,
            "events": [e.as_dict() for e in self.events],
            "per_channel": {k: round(v, 4) for k, v in self.per_channel.items()},
            "threshold": self.threshold,
            "detail": self.detail,
            "skipped_reason": self.skipped_reason,
        }
        if duration:
            out["contaminated_seconds"] = round(self.contaminated_seconds(), 3)
            out["contaminated_fraction"] = round(
                min(1.0, self.contaminated_seconds() / duration), 4
            )
            out["per_minute"] = round(self.rate_per_minute(duration), 2)
        return out


def robust_z(x: np.ndarray, axis: int = -1) -> np.ndarray:
    """Z-score using median and MAD.

    Artifacts are exactly the outliers we are looking for, so a mean/SD z-score
    lets them inflate their own baseline and hide. MAD does not.
    """
    med = np.median(x, axis=axis, keepdims=True)
    mad = np.median(np.abs(x - med), axis=axis, keepdims=True)
    # 1.4826 makes MAD a consistent estimator of SD for Gaussian data.
    scale = mad * 1.4826
    scale = np.where(scale <= 0, np.finfo(float).eps, scale)
    return (x - med) / scale


def merge_events(events: list[ArtifactEvent], gap: float = 0.0) -> list[ArtifactEvent]:
    """Merge events of one kind that overlap or sit within ``gap`` seconds."""
    if not events:
        return []
    ordered = sorted(events, key=lambda e: e.onset)
    out = [ordered[0]]
    for ev in ordered[1:]:
        last = out[-1]
        if ev.onset <= last.offset + gap:
            new_end = max(last.offset, ev.offset)
            last.duration = new_end - last.onset
            last.severity = max(last.severity, ev.severity)
            for c in ev.channels:
                if c not in last.channels:
                    last.channels.append(c)
        else:
            out.append(ev)
    return out


def usable_band(sfreq: float, low: float, high: float) -> tuple[float, float] | None:
    """Clamp a filter band to what ``sfreq`` can actually represent.

    Consumer headsets sample at 256 Hz, so a textbook 110-140 Hz muscle band is
    simply unavailable. Returns ``None`` when nothing usable is left, which the
    caller must report as a skip rather than a clean result.
    """
    nyq = sfreq / 2.0
    hi = min(high, nyq * 0.9)
    lo = max(low, 0.1)
    if hi <= lo + 1.0:
        return None
    return lo, hi
