"""Mains line-noise detection.

Power infrastructure runs at 50 Hz (most of the world) or 60 Hz (the Americas,
and parts of Asia). Poor electrode contact turns the head into an antenna for
it, so a sharp peak at one of those frequencies -- and its harmonics -- is a
direct read on how well the cap was applied.

Reported as a signal-to-neighbour ratio in dB rather than raw power, so it does
not depend on the recording's amplitude scale.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ..recording import Recording
from .base import LINE_NOISE, DetectorResult

CANDIDATES = (50.0, 60.0)
# Half-width of the peak window, and of the baseline shoulders either side.
PEAK_HW = 1.5
SHOULDER = 6.0
# dB above the local baseline before we call it contamination worth reporting.
DEFAULT_DB = 6.0


def _band_power(freqs: np.ndarray, psd: np.ndarray, lo: float, hi: float) -> np.ndarray:
    mask = (freqs >= lo) & (freqs <= hi)
    if not mask.any():
        return np.zeros(psd.shape[0])
    return psd[:, mask].mean(axis=1)


def _peak_db(freqs: np.ndarray, psd: np.ndarray, f0: float) -> np.ndarray:
    """dB by which the band around ``f0`` exceeds its immediate neighbours."""
    peak = _band_power(freqs, psd, f0 - PEAK_HW, f0 + PEAK_HW)
    left = _band_power(freqs, psd, f0 - SHOULDER, f0 - PEAK_HW * 1.5)
    right = _band_power(freqs, psd, f0 + PEAK_HW * 1.5, f0 + SHOULDER)

    shoulders = np.vstack([left, right])
    # Median of the two shoulders resists a harmonic sitting on one of them.
    baseline = np.median(shoulders, axis=0)
    baseline = np.where(baseline <= 0, np.finfo(float).eps, baseline)
    return 10.0 * np.log10(np.maximum(peak, np.finfo(float).eps) / baseline)


def detect_line_noise(rec: Recording, *, db_threshold: float = DEFAULT_DB) -> DetectorResult:
    """Identify mains contamination and which frequency it is on."""
    res = DetectorResult(kind=LINE_NOISE)

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res

    nyq = rec.sfreq / 2.0
    usable = [f for f in CANDIDATES if f + SHOULDER < nyq]
    if not usable:
        res.skipped_reason = (
            f"sample rate {rec.sfreq:g} Hz cannot resolve 50 or 60 Hz "
            f"(Nyquist {nyq:g} Hz)"
        )
        return res

    # 2 s windows give ~0.5 Hz resolution, enough to separate a mains peak from
    # its neighbours without smearing it.
    nperseg = int(min(rec.n_samples, max(rec.sfreq * 2, 256)))
    if nperseg < 64:
        res.skipped_reason = "recording too short for a spectral estimate"
        return res

    freqs, psd = sps.welch(rec.data, fs=rec.sfreq, nperseg=nperseg, axis=-1)

    scores = {f: _peak_db(freqs, psd, f) for f in usable}
    # The mains frequency is whichever candidate is more prominent head-wide.
    best = max(usable, key=lambda f: float(np.median(scores[f])))
    per_ch = scores[best]

    res.threshold = db_threshold
    res.per_channel = {n: float(per_ch[i]) for i, n in enumerate(rec.ch_names)}

    affected = [rec.ch_names[i] for i in np.flatnonzero(per_ch >= db_threshold)]
    res.detail = {
        "line_frequency_hz": best,
        "median_db": float(np.median(per_ch)),
        "max_db": float(per_ch.max()),
        "affected_channels": affected,
        "n_affected": len(affected),
        "other_candidate_db": {
            str(int(f)): float(np.median(scores[f])) for f in usable if f != best
        },
        # Line noise is continuous, not episodic, so it is reported as a
        # per-channel level rather than as timed events. Scoring treats it as a
        # channel-quality term, not as contaminated time.
        "note": (
            f"{best:.0f} Hz mains detected on {len(affected)} of {rec.n_channels} channels."
            if affected
            else f"No {best:.0f} Hz mains contamination above {db_threshold:g} dB."
        ),
    }
    return res
