"""Eye-blink detection.

A blink is a large, slow, frontally-dominant deflection: roughly 100-400 uV
peak, 100-400 ms wide, concentrated at Fp1/Fp2/AF7/AF8 because the eye is an
electrical dipole sitting right underneath those electrodes.

Two paths, deliberately sharing one code path after the signal is built:

* **With EOG electrodes** — use them directly. This is the reference case, and
  what dataset 02 provides.
* **Without** — build a *virtual EOG* from frontal EEG. This is the case that
  actually matters: no consumer headset has EOG electrodes, so if the tool only
  worked with them it would be useless for the hardware most people own.

``validate/v2_reference_free.py`` scores the second path against the first.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ..recording import Recording
from ..triage import virtual_eog_index
from .base import BLINK, ArtifactEvent, DetectorResult, robust_z, usable_band

# A blink's energy sits well under 10 Hz; the low cut removes drift.
BAND = (1.0, 10.0)

# Physiological limits. A deflection lasting seconds is drift or movement, not
# a blink.
MAX_WIDTH_S = 1.2
TYPICAL_WIDTH_S = 0.3

# --- Calibrated constants -------------------------------------------------
# Swept over 12 subjects x 4 devices (~48 recordings) of dataset 01 against its
# cued beep timestamps; see validate/v1_cued_events.py. The chosen point gives
# ~96% recall of cued blinks at 1.03 detections per cued blink -- i.e. one
# detection per blink, which is the property that matters for a rate estimate.
#
# The 0.8 s refractory period is the one real trade-off: genuine blink flutter
# closer than that merges into a single event. Accepted because contaminated
# *time* is what scoring uses, and merging barely changes it, while splitting
# one blink into three (which 0.25 s did) inflated rates by 3.5x.
MIN_SPACING_S = 0.8
SMOOTH_S = 0.5
DEFAULT_Z = 4.0


def build_eog_signal(rec: Recording) -> tuple[np.ndarray, list[str], bool]:
    """Return ``(signal, source_channels, used_real_eog)``.

    Averaging the frontal channels suppresses uncorrelated neural activity while
    the blink, which is common to all of them, survives.
    """
    eog_idx = rec.picks("eog")
    if eog_idx:
        names = [rec.ch_names[i] for i in eog_idx]
        return rec.data[eog_idx].mean(axis=0), names, True

    idx = virtual_eog_index(rec)
    names = [rec.ch_names[i] for i in idx]
    return rec.data[idx].mean(axis=0), names, False


def detect_blinks(
    rec: Recording,
    *,
    z_threshold: float = DEFAULT_Z,
    min_spacing_s: float = MIN_SPACING_S,
    smooth_s: float = SMOOTH_S,
) -> DetectorResult:
    """Find blinks in ``rec``."""
    res = DetectorResult(kind=BLINK)

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res

    band = usable_band(rec.sfreq, *BAND)
    if band is None:
        res.skipped_reason = f"sample rate {rec.sfreq:g} Hz too low for a 1-10 Hz band"
        return res

    raw_signal, sources, used_real = build_eog_signal(rec)
    if raw_signal.size < int(rec.sfreq):
        res.skipped_reason = "recording shorter than one second"
        return res

    sos = sps.butter(4, band, btype="band", fs=rec.sfreq, output="sos")
    filtered = sps.sosfiltfilt(sos, raw_signal)

    # A blink is triphasic: the deflection overshoots, rebounds, and undershoots.
    # Peak-picking on |signal| therefore splits one blink into three detections
    # ~0.45 s apart, which is wider than any sane refractory period. Taking the
    # analytic envelope collapses the whole complex into a single bump, so one
    # blink counts once regardless of montage polarity.
    envelope = np.abs(sps.hilbert(filtered))

    # Smooth over roughly one blink so residual ripple inside the complex does
    # not re-split it.
    win = max(3, int(round(smooth_s * rec.sfreq)) | 1)
    kernel = sps.windows.hann(win)
    kernel /= kernel.sum()
    envelope = np.convolve(envelope, kernel, mode="same")

    z = robust_z(envelope)

    peaks, props = sps.find_peaks(
        z,
        height=z_threshold,
        distance=max(1, int(min_spacing_s * rec.sfreq)),
    )

    # Width at half prominence, bounded to physiological plausibility.
    if peaks.size:
        widths, _, left, right = sps.peak_widths(z, peaks, rel_height=0.5)
    else:
        widths = left = right = np.array([])

    events: list[ArtifactEvent] = []
    kept_heights: list[float] = []
    for k, p in enumerate(peaks):
        width_s = float(widths[k]) / rec.sfreq if widths.size else TYPICAL_WIDTH_S
        if width_s > MAX_WIDTH_S:
            # Too long to be a blink -- drift or movement owns this one.
            continue
        onset = float(left[k]) / rec.sfreq if left.size else p / rec.sfreq
        duration = max(width_s, 0.05)
        height = float(props["peak_heights"][k])
        kept_heights.append(height)
        events.append(
            ArtifactEvent(
                onset=max(0.0, onset),
                duration=duration,
                kind=BLINK,
                # Saturates at 4x threshold so one huge blink cannot dominate.
                severity=float(np.clip((height - z_threshold) / (3 * z_threshold), 0, 1)),
                channels=list(sources),
            )
        )

    res.events = events
    res.threshold = z_threshold
    res.detail = {
        "used_real_eog": used_real,
        "source_channels": sources,
        "band_hz": list(band),
        "median_peak_z": float(np.median(kept_heights)) if kept_heights else None,
        "rejected_too_wide": int(peaks.size - len(events)),
    }

    # Per-channel blink amplitude, in microvolts, at the peak times. This is
    # what the Device Report Card compares across headsets: how badly a blink
    # contaminates each electrode.
    if events:
        centres = np.array([int((e.onset + e.duration / 2) * rec.sfreq) for e in events])
        centres = centres[(centres >= 0) & (centres < rec.n_samples)]
        if centres.size:
            half = max(1, int(0.15 * rec.sfreq))
            for i, name in enumerate(rec.ch_names):
                amps = [
                    np.ptp(rec.data[i, max(0, c - half) : min(rec.n_samples, c + half)])
                    for c in centres
                ]
                res.per_channel[name] = float(np.median(amps)) * 1e6

    return res
