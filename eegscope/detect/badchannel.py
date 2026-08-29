"""Bad-channel detection, following the PREP pipeline's criteria.

Bigdely-Shamlo et al. (2015) established the standard set of tests, and this
implements the ones that need no electrode coordinates, so they work on a
4-channel headband as well as a 64-channel cap:

* **flat** -- no signal at all (dead electrode or unplugged input)
* **deviation** -- amplitude wildly out of step with the other channels
* **correlation** -- fails to agree with any other channel; real EEG is
  spatially smooth, so a channel correlating with nothing is measuring itself.
  Note this cuts both ways: artifacts are *common-mode* and push correlation
  up, so a high value is not evidence of cleanliness. Measured on a Muse 2,
  frontal channels correlate 0.41 at rest and 0.88 while the subject blinks.
* **high-frequency noise** -- poor contact shows up as excess power above the
  physiological band, measured *relative to the other channels in the same
  recording* rather than against a fixed cutoff. A fixed cutoff on a ratio is
  self-defeating: a large low-frequency artifact inflates total power and makes
  a genuinely noisy electrode look clean. On a Muse 2 that inverted the result
  outright -- three of four channels were flagged during quiet rest and none
  during heavy blinking.

Correlation needs a dense montage to mean anything, and is skipped otherwise
rather than silently passed. PREP was designed for 32+ electrode caps where
neighbours sit centimetres apart. On a 4-electrode headband (Muse 2: TP9, AF7,
AF8, TP10) the electrodes are on opposite sides of the head and genuinely
should not correlate -- applying the test there flagged AF7/AF8 as broken
during quiet rest and passed them during heavy blinking, i.e. exactly
backwards.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ..recording import Recording
from .base import DetectorResult, robust_z

# Robust-z beyond which a channel's amplitude is considered out of family.
DEVIATION_Z = 5.0
# A channel should correlate at least this well with its best-matching partner.
MIN_CORRELATION = 0.35
# High-frequency noise is judged against the other channels (robust z), with an
# absolute ceiling as a backstop for the case where *every* channel is bad.
HF_OUTLIER_Z = 4.0
ABSOLUTE_MAX_HF_RATIO = 0.80
MIN_CHANNELS_FOR_HF_OUTLIER = 4
# Below this the montage is too sparse for "agrees with its neighbours" to be a
# meaningful question -- see the module docstring.
MIN_CHANNELS_FOR_CORRELATION = 8

# Correlation is computed on 1 s windows so a brief artifact cannot make a good
# channel look uncorrelated across the whole recording.
WINDOW_S = 1.0


def _windowed_max_correlation(data: np.ndarray, sfreq: float) -> np.ndarray:
    """Median over windows of each channel's best correlation with any other."""
    n_ch, n_samp = data.shape
    win = max(int(WINDOW_S * sfreq), 32)
    n_win = max(1, n_samp // win)

    best_per_window = np.zeros((n_ch, n_win))
    for w in range(n_win):
        seg = data[:, w * win : (w + 1) * win]
        if seg.shape[1] < 8:
            continue
        seg = seg - seg.mean(axis=1, keepdims=True)
        sd = seg.std(axis=1)
        sd = np.where(sd <= 0, np.finfo(float).eps, sd)
        corr = (seg @ seg.T) / (seg.shape[1] * np.outer(sd, sd))
        np.fill_diagonal(corr, 0.0)
        best_per_window[:, w] = np.abs(corr).max(axis=1)

    return np.median(best_per_window, axis=1)


def _hf_ratio(data: np.ndarray, sfreq: float) -> np.ndarray:
    """Power above 40 Hz as a fraction of total, per channel."""
    nyq = sfreq / 2.0
    if nyq <= 45.0:
        return np.zeros(data.shape[0])
    nperseg = int(min(data.shape[1], max(sfreq * 2, 256)))
    freqs, psd = sps.welch(data, fs=sfreq, nperseg=nperseg, axis=-1)
    total = psd.sum(axis=1)
    total = np.where(total <= 0, np.finfo(float).eps, total)
    hf = psd[:, freqs >= 40.0].sum(axis=1)
    return hf / total


def detect_bad_channels(
    rec: Recording,
    *,
    deviation_z: float = DEVIATION_Z,
    min_correlation: float = MIN_CORRELATION,
    hf_outlier_z: float = HF_OUTLIER_Z,
) -> DetectorResult:
    """Flag channels that should not be trusted, with a reason for each."""
    res = DetectorResult(kind="bad_channel")

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res
    if rec.n_samples < int(rec.sfreq):
        res.skipped_reason = "recording shorter than one second"
        return res

    reasons: dict[str, list[str]] = {n: [] for n in rec.ch_names}

    # -- flat --------------------------------------------------------------
    sd = rec.data.std(axis=1)
    finite = sd[np.isfinite(sd) & (sd > 0)]
    scale = float(np.median(finite)) if finite.size else 0.0
    flat_mask = (sd <= max(scale * 1e-6, 1e-15)) | ~np.isfinite(sd)
    for i in np.flatnonzero(flat_mask):
        reasons[rec.ch_names[i]].append("flat")

    # -- amplitude deviation ----------------------------------------------
    # Log scale: channel amplitudes are multiplicative, so a linear z-score is
    # dominated by whichever channel happens to be largest.
    with np.errstate(divide="ignore"):
        log_sd = np.log10(np.where(sd > 0, sd, np.nan))
    dev_z = np.full(rec.n_channels, np.nan)
    valid = np.isfinite(log_sd)
    if valid.sum() >= 3:
        dev_z[valid] = robust_z(log_sd[valid])
        for i in np.flatnonzero(np.abs(np.nan_to_num(dev_z)) >= deviation_z):
            reasons[rec.ch_names[i]].append("amplitude deviation")

    # -- correlation -------------------------------------------------------
    corr = np.full(rec.n_channels, np.nan)
    corr_ran = rec.n_channels >= MIN_CHANNELS_FOR_CORRELATION
    if corr_ran:
        corr = _windowed_max_correlation(rec.data, rec.sfreq)
        for i in np.flatnonzero(corr < min_correlation):
            if not flat_mask[i]:  # a flat channel is already accounted for
                reasons[rec.ch_names[i]].append("uncorrelated with all others")

    # -- high-frequency noise ---------------------------------------------
    hf = _hf_ratio(rec.data, rec.sfreq)
    hf_z = np.full(rec.n_channels, np.nan)
    hf_ran = bool(np.any(hf > 0))
    if hf_ran:
        if rec.n_channels >= MIN_CHANNELS_FOR_HF_OUTLIER:
            hf_z = robust_z(hf)
            outliers = np.flatnonzero(np.nan_to_num(hf_z) >= hf_outlier_z)
        else:
            outliers = np.array([], dtype=int)
        for i in outliers:
            reasons[rec.ch_names[i]].append("excess high-frequency noise")
        # Backstop: if the whole montage is bad, the relative test sees nothing.
        for i in np.flatnonzero(hf > ABSOLUTE_MAX_HF_RATIO):
            if "excess high-frequency noise" not in reasons[rec.ch_names[i]]:
                reasons[rec.ch_names[i]].append("excess high-frequency noise")

    bad = {n: r for n, r in reasons.items() if r}

    # Score per channel: 0 = clean, 1 = definitively bad.
    for i, name in enumerate(rec.ch_names):
        res.per_channel[name] = min(1.0, len(reasons[name]) / 2.0)

    res.detail = {
        "bad_channels": sorted(bad),
        "n_bad": len(bad),
        "n_total": rec.n_channels,
        "reasons": bad,
        "metrics": {
            n: {
                "sd_uv": round(float(sd[i]) * 1e6, 3),
                "deviation_z": None if not np.isfinite(dev_z[i]) else round(float(dev_z[i]), 2),
                "max_correlation": None if not np.isfinite(corr[i]) else round(float(corr[i]), 3),
                "hf_ratio": round(float(hf[i]), 3) if hf_ran else None,
                "hf_outlier_z": None if not np.isfinite(hf_z[i]) else round(float(hf_z[i]), 2),
            }
            for i, n in enumerate(rec.ch_names)
        },
        "checks_run": {
            "flat": True,
            "deviation": bool(valid.sum() >= 3),
            "correlation": corr_ran,
            "high_frequency": hf_ran,
        },
        "checks_skipped_note": (
            None
            if corr_ran
            else f"Correlation check needs >= {MIN_CHANNELS_FOR_CORRELATION} channels; "
            f"this recording has {rec.n_channels}. Electrodes on a sparse "
            "headset sit too far apart to be cross-checked against each other."
        ),
    }
    return res
