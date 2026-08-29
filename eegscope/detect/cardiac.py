"""Heartbeat (cardiac) artifact detection.

The QRS complex couples into EEG through nearby vessels and through the
reference electrode when it sits on a mastoid. It is small but relentlessly
periodic at roughly 1 Hz, which is what makes it findable.

Two very different confidence levels, and the difference is reported rather
than hidden:

* **With an ECG channel** -- straightforward QRS detection. Reliable.
* **Without** -- infer it from periodicity in the EEG itself. This is genuinely
  hard and prone to false positives from any other rhythmic activity, so the
  result is marked low-confidence and requires a plausible heart rate before it
  reports anything at all.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ..recording import Recording
from .base import CARDIAC, ArtifactEvent, DetectorResult, robust_z, usable_band

QRS_BAND = (8.0, 20.0)
# Plausible resting-to-active human heart rate.
MIN_BPM = 40.0
MAX_BPM = 180.0
QRS_WIDTH_S = 0.12

DEFAULT_Z = 3.0
# Without an ECG reference we require the beat train to be strongly regular
# before believing it. Coefficient of variation of the inter-beat interval.
MAX_IBI_CV = 0.25


def _find_beats(signal_1d: np.ndarray, sfreq: float, z_threshold: float) -> np.ndarray:
    band = usable_band(sfreq, *QRS_BAND)
    if band is None:
        return np.array([], dtype=int)
    sos = sps.butter(4, band, btype="band", fs=sfreq, output="sos")
    filtered = sps.sosfiltfilt(sos, signal_1d)

    # Squaring emphasises the sharp QRS over smoother rhythms before smoothing
    # turns each complex into a single bump -- the classic Pan-Tompkins shape.
    energy = filtered**2
    win = max(3, int(round(QRS_WIDTH_S * sfreq)) | 1)
    kernel = np.ones(win) / win
    smoothed = np.convolve(energy, kernel, mode="same")

    z = robust_z(smoothed)
    min_gap = int((60.0 / MAX_BPM) * sfreq)
    peaks, _ = sps.find_peaks(z, height=z_threshold, distance=max(1, min_gap))
    return peaks


def detect_cardiac(rec: Recording, *, z_threshold: float = DEFAULT_Z) -> DetectorResult:
    """Find heartbeat contamination."""
    res = DetectorResult(kind=CARDIAC)

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res
    if rec.duration < 10.0:
        res.skipped_reason = f"recording is {rec.duration:.1f}s; need at least 10s of beats"
        return res

    ecg_idx = rec.picks("ecg")
    used_real = bool(ecg_idx)

    if used_real:
        source = rec.data[ecg_idx].mean(axis=0)
        sources = [rec.ch_names[i] for i in ecg_idx]
    else:
        # No ECG: the cardiac component is common-mode across the montage, so
        # the channel average is the best available proxy.
        source = rec.data.mean(axis=0)
        sources = list(rec.ch_names)

    peaks = _find_beats(source, rec.sfreq, z_threshold)

    if peaks.size < 4:
        res.detail = {
            "used_real_ecg": used_real,
            "confidence": "high" if used_real else "low",
            "note": "Too few candidate beats to establish a rhythm.",
            "bpm": None,
        }
        return res

    ibi = np.diff(peaks) / rec.sfreq
    bpm = 60.0 / float(np.median(ibi))
    cv = float(np.std(ibi) / np.mean(ibi)) if np.mean(ibi) > 0 else 1.0

    plausible = MIN_BPM <= bpm <= MAX_BPM
    regular = cv <= MAX_IBI_CV

    # Without an ECG reference, only a plausible *and* regular train counts.
    # Anything less is far more likely to be alpha or a movement rhythm.
    accept = plausible if used_real else (plausible and regular)

    events: list[ArtifactEvent] = []
    if accept:
        for p in peaks:
            events.append(
                ArtifactEvent(
                    onset=max(0.0, p / rec.sfreq - QRS_WIDTH_S / 2),
                    duration=QRS_WIDTH_S,
                    kind=CARDIAC,
                    severity=0.3 if not used_real else 0.5,
                    channels=list(sources) if used_real else [],
                )
            )

    res.events = events
    res.threshold = z_threshold
    res.detail = {
        "used_real_ecg": used_real,
        "confidence": "high" if used_real else "low",
        "source_channels": sources if used_real else ["<channel average>"],
        "bpm": round(bpm, 1),
        "ibi_cv": round(cv, 3),
        "plausible_rate": plausible,
        "regular_rhythm": regular,
        "accepted": accept,
        "note": (
            f"Detected from a dedicated ECG channel at {bpm:.0f} bpm."
            if used_real and accept
            else f"Inferred from EEG periodicity at {bpm:.0f} bpm (low confidence)."
            if accept
            else f"Candidate rhythm at {bpm:.0f} bpm rejected: "
            + ("rate implausible" if not plausible else "rhythm too irregular")
            + ". Without an ECG channel this is not distinguishable from other "
            "periodic activity."
        ),
    }
    return res
