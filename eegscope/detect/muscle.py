"""Muscle / jaw-clench detection.

Scalp EMG from the temporalis and masseter muscles is broadband and fast,
sitting well above the ~30 Hz where real cortical rhythms have most of their
power. So the signature is a burst of high-frequency energy, strongest at
temporal electrodes, lasting as long as the clench.

The awkward part is sample rate. The textbook muscle band is 110-140 Hz, which
needs >=280 Hz sampling. Half the devices here run at 256 Hz, so that band does
not exist for them. Rather than silently return "clean" for a headset that
physically cannot see muscle noise, the band is adapted to the available
bandwidth and the choice is reported -- and if nothing usable is left, the
detector marks itself skipped.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from ..recording import Recording
from .base import (
    MUSCLE,
    ArtifactEvent,
    DetectorResult,
    effective_bandwidth,
    head_wide,
    merge_events,
    robust_z,
)

# Preferred band, and the lowest we will accept before calling it hopeless.
PREFERRED_BAND = (110.0, 140.0)
BAND_WIDTH = 30.0
MIN_USABLE_LOW = 35.0
MIN_USABLE_HIGH = 65.0
# Fraction of Nyquist we are willing to filter up to before the anti-alias
# roll-off makes the band meaningless.
NYQUIST_FRACTION = 0.93

# A clench lasts hundreds of ms to seconds.
SMOOTH_S = 0.25
MIN_DURATION_S = 0.1
MERGE_GAP_S = 0.2

DEFAULT_Z = 4.0


def _choose_band(sfreq: float, max_freq: float | None = None) -> tuple[tuple[float, float] | None, str]:
    """Pick the *highest* narrow muscle band this sample rate can represent.

    Measured on dataset 01's cued jaw-clench vs blink recordings: widening the
    band downward to 20 Hz to "capture more muscle" badly hurts specificity,
    because real cortical rhythms and blink/movement energy live below ~40 Hz.
    A 20-135 Hz band fired almost as often during blinking as during clenching
    (1.4x separation on the DSI-24); the highest available 30 Hz window raised
    that to 2.6x on the same recordings, and 24x on a 512 Hz device.

    So: take the top of what the device can see, and keep the window narrow.
    """
    ceiling = (sfreq / 2.0) * NYQUIST_FRACTION
    if max_freq is not None:
        # Never measure above where the recording still has real signal.
        ceiling = min(ceiling, max_freq)
    hi = min(PREFERRED_BAND[1], ceiling)
    if hi < MIN_USABLE_HIGH:
        return None, "unavailable"
    lo = max(MIN_USABLE_LOW, hi - BAND_WIDTH)
    if hi - lo < 10.0:
        return None, "unavailable"
    mode = "preferred" if (lo, hi) == PREFERRED_BAND else "adapted"
    return (lo, hi), mode


def detect_muscle(
    rec: Recording,
    *,
    z_threshold: float = DEFAULT_Z,
    smooth_s: float = SMOOTH_S,
) -> DetectorResult:
    """Find muscle/jaw-clench bursts in ``rec``."""
    res = DetectorResult(kind=MUSCLE)

    if rec.n_channels == 0:
        res.skipped_reason = "no channels to analyse"
        return res

    bandwidth = effective_bandwidth(rec.data, rec.sfreq)
    band, mode = _choose_band(rec.sfreq, max_freq=bandwidth)
    if band is None:
        nyq_limit = MIN_USABLE_HIGH / NYQUIST_FRACTION * 2
        if bandwidth < MIN_USABLE_HIGH:
            res.skipped_reason = (
                f"this recording carries no signal above {bandwidth:.0f} Hz "
                f"(sampled at {rec.sfreq:g} Hz but low-passed well below it), so "
                "muscle contamination cannot be measured"
            )
        else:
            res.skipped_reason = (
                f"sample rate {rec.sfreq:g} Hz cannot represent a muscle band "
                f"(need >= {nyq_limit:.0f} Hz)"
            )
        res.detail = {"effective_bandwidth_hz": round(bandwidth, 1), "sfreq": rec.sfreq}
        return res

    if rec.n_samples < int(rec.sfreq * 2):
        res.skipped_reason = "recording shorter than two seconds"
        return res

    sos = sps.butter(4, band, btype="band", fs=rec.sfreq, output="sos")
    filtered = sps.sosfiltfilt(sos, rec.data, axis=-1)
    envelope = np.abs(sps.hilbert(filtered, axis=-1))

    win = max(3, int(round(smooth_s * rec.sfreq)) | 1)
    kernel = sps.windows.hann(win)
    kernel /= kernel.sum()
    smoothed = np.apply_along_axis(lambda v: np.convolve(v, kernel, mode="same"), -1, envelope)

    # Per-channel z, collapsed with a high percentile rather than a max: a max
    # scales with how many electrodes are watching, which made dense caps look
    # dirty. See head_wide().
    z = robust_z(smoothed, axis=-1)
    z_max = head_wide(z)
    hot_channel = z.argmax(axis=0)

    above = z_max >= z_threshold
    events: list[ArtifactEvent] = []
    if above.any():
        edges = np.diff(above.astype(np.int8))
        starts = list(np.flatnonzero(edges == 1) + 1)
        stops = list(np.flatnonzero(edges == -1) + 1)
        if above[0]:
            starts.insert(0, 0)
        if above[-1]:
            stops.append(len(above))

        for s, e in zip(starts, stops):
            duration = (e - s) / rec.sfreq
            if duration < MIN_DURATION_S:
                continue
            peak = float(z_max[s:e].max())
            chans = sorted({rec.ch_names[c] for c in hot_channel[s:e]})
            events.append(
                ArtifactEvent(
                    onset=s / rec.sfreq,
                    duration=duration,
                    kind=MUSCLE,
                    severity=float(np.clip((peak - z_threshold) / (3 * z_threshold), 0, 1)),
                    channels=chans,
                )
            )

    res.events = merge_events(events, gap=MERGE_GAP_S)
    res.threshold = z_threshold
    res.detail = {
        "band_hz": [round(b, 1) for b in band],
        "band_mode": mode,
        "sfreq": rec.sfreq,
        "effective_bandwidth_hz": round(bandwidth, 1),
        # Made explicit because a 256 Hz headset genuinely cannot see the
        # 110-140 Hz band, and a reader should know the number is not
        # comparable with a 1000 Hz recording's.
        "band_note": (
            "Preferred 110-140 Hz band used."
            if mode == "preferred"
            else f"Sample rate forced an adapted {band[0]:.0f}-{band[1]:.0f} Hz band; "
            "muscle power above the Nyquist limit is invisible to this recording."
        ),
        "n_channels_scanned": rec.n_channels,
        "head_wide_statistic": "90th percentile across channels",
    }

    # Fraction of time each channel spent above threshold: this is what points
    # at *which* electrode the clench sits under.
    for i, name in enumerate(rec.ch_names):
        res.per_channel[name] = float((z[i] >= z_threshold).mean())

    return res
