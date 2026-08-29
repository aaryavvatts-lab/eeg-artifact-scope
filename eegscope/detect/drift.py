"""Drift and movement detection.

Slow, large excursions below ~1 Hz: sweat, electrode settling, cable pull, head
movement. Distinct from a blink, which is faster and frontally confined, and
from muscle, which is fast and broadband.

Also flags **electrode pops** -- sudden step changes from a contact breaking and
re-making. Those are steps rather than bumps, so they are found on the
derivative instead of the envelope.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ..recording import Recording
from .base import (
    DRIFT,
    POP,
    ArtifactEvent,
    DetectorResult,
    head_wide,
    merge_events,
    robust_z,
)

DRIFT_BAND = (0.1, 1.0)
DRIFT_SMOOTH_S = 1.0
DRIFT_MIN_DURATION_S = 0.5
DRIFT_MERGE_GAP_S = 0.5
DRIFT_Z = 4.0

# A pop is a near-instantaneous jump; it stands far out on the sample-to-sample
# difference even when the absolute amplitude is unremarkable.
POP_Z = 8.0
POP_DURATION_S = 0.1
POP_MERGE_GAP_S = 0.05

# --- Absolute floors ------------------------------------------------------
# A purely relative threshold cannot measure absolute quality: z-scoring against
# a recording's own median always flags a few percent of it, however clean it
# is. Measured on dataset 03 (a quiet, heavily filtered clinical recording),
# relative-only thresholds claimed 48% drift and 76 pops/min on data whose slow
# envelope never exceeds 12 uV and whose steps never exceed 27 uV.
#
# So an event must be BOTH unusual for this recording AND physically large
# enough to matter. These floors follow the conventional EEG rejection range
# (100-150 uV peak-to-peak); the drift floor is an envelope, so ~2x it in p-p.
MIN_DRIFT_UV = 75.0
MIN_POP_STEP_UV = 50.0


def _smooth(x: np.ndarray, sfreq: float, seconds: float) -> np.ndarray:
    win = max(3, int(round(seconds * sfreq)) | 1)
    kernel = sps.windows.hann(win)
    kernel /= kernel.sum()
    return np.apply_along_axis(lambda v: np.convolve(v, kernel, mode="same"), -1, x)


def _spans(mask: np.ndarray) -> list[tuple[int, int]]:
    if not mask.any():
        return []
    edges = np.diff(mask.astype(np.int8))
    starts = list(np.flatnonzero(edges == 1) + 1)
    stops = list(np.flatnonzero(edges == -1) + 1)
    if mask[0]:
        starts.insert(0, 0)
    if mask[-1]:
        stops.append(len(mask))
    return list(zip(starts, stops))


def detect_drift(
    rec: Recording,
    *,
    z_threshold: float = DRIFT_Z,
    min_amplitude_uv: float = MIN_DRIFT_UV,
) -> DetectorResult:
    """Find slow drift and movement excursions."""
    res = DetectorResult(kind=DRIFT)

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res

    # A 0.1 Hz component needs several cycles to be distinguishable from a
    # trend; below ~20 s there is nothing meaningful to measure.
    if rec.duration < 20.0:
        res.skipped_reason = f"recording is {rec.duration:.1f}s; drift needs at least 20s"
        return res

    sos = sps.butter(2, DRIFT_BAND, btype="band", fs=rec.sfreq, output="sos")
    filtered = sps.sosfiltfilt(sos, rec.data, axis=-1)
    envelope = _smooth(np.abs(sps.hilbert(filtered, axis=-1)), rec.sfreq, DRIFT_SMOOTH_S)

    z = robust_z(envelope, axis=-1)
    z_max = head_wide(z)
    hot = z.argmax(axis=0)

    # Both criteria must hold: unusual for this recording, and large in volts.
    amplitude_uv = envelope.max(axis=0) * 1e6
    flagged = (z_max >= z_threshold) & (amplitude_uv >= min_amplitude_uv)

    events = []
    for s, e in _spans(flagged):
        duration = (e - s) / rec.sfreq
        if duration < DRIFT_MIN_DURATION_S:
            continue
        peak = float(z_max[s:e].max())
        events.append(
            ArtifactEvent(
                onset=s / rec.sfreq,
                duration=duration,
                kind=DRIFT,
                severity=float(np.clip((peak - z_threshold) / (3 * z_threshold), 0, 1)),
                channels=sorted({rec.ch_names[c] for c in hot[s:e]}),
            )
        )

    res.events = merge_events(events, gap=DRIFT_MERGE_GAP_S)
    res.threshold = z_threshold
    res.per_channel = {
        n: float(((z[i] >= z_threshold) & (envelope[i] * 1e6 >= min_amplitude_uv)).mean())
        for i, n in enumerate(rec.ch_names)
    }
    res.detail = {
        "band_hz": list(DRIFT_BAND),
        "smooth_s": DRIFT_SMOOTH_S,
        "min_amplitude_uv": min_amplitude_uv,
        "peak_amplitude_uv": round(float(amplitude_uv.max()), 1),
    }
    return res


def detect_pops(
    rec: Recording,
    *,
    z_threshold: float = POP_Z,
    min_step_uv: float = MIN_POP_STEP_UV,
) -> DetectorResult:
    """Find electrode pops: abrupt steps from a contact breaking."""
    res = DetectorResult(kind=POP)

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res
    if rec.n_samples < 16:
        res.skipped_reason = "recording too short"
        return res

    diff = np.diff(rec.data, axis=-1, prepend=rec.data[:, :1])
    z = np.abs(robust_z(diff, axis=-1))
    z_max = z.max(axis=0)
    hot = z.argmax(axis=0)

    step_uv = np.abs(diff).max(axis=0) * 1e6
    flagged = (z_max >= z_threshold) & (step_uv >= min_step_uv)

    events = []
    for idx in np.flatnonzero(flagged):
        peak = float(z_max[idx])
        events.append(
            ArtifactEvent(
                onset=max(0.0, idx / rec.sfreq - POP_DURATION_S / 2),
                duration=POP_DURATION_S,
                kind=POP,
                severity=float(np.clip((peak - z_threshold) / (3 * z_threshold), 0, 1)),
                channels=[rec.ch_names[hot[idx]]],
            )
        )

    res.events = merge_events(events, gap=POP_MERGE_GAP_S)
    res.threshold = z_threshold
    res.per_channel = {
        n: float(((z[i] >= z_threshold) & (np.abs(diff[i]) * 1e6 >= min_step_uv)).mean())
        for i, n in enumerate(rec.ch_names)
    }
    res.detail = {
        "n_raw_samples_flagged": int(flagged.sum()),
        "min_step_uv": min_step_uv,
        "largest_step_uv": round(float(step_uv.max()), 1),
        "note": (
            "Measured on the sample-to-sample derivative, where a step dominates. "
            f"Requires both an outlier (z>={z_threshold:g}) and a real jump "
            f"(>={min_step_uv:g} uV)."
        ),
    }
    return res
