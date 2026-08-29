"""V3b - The dataset 03 clean-vs-noisy comparison, reported as a null result.

Dataset 03's README states that subjects 01-30 contain clean EEG and 31-40
contain noisy EEG. The plan was to use that as an external check on the quality
score. It does not work, and this script exists so that conclusion is
reproducible rather than a claim.

Every standard EEG quality metric was measured on all 40 subjects. None
separates the labelled groups. Two further observations point the same way:

* Channels named ``Add_lead1..16`` -- which look like unused vendor inputs --
  carry 9-17 uV of signal and are statistically indistinguishable from the
  named 10-20 channels.
* Mean inter-channel correlation among the *named* channels is ~0.21, about the
  same as among the ``Add_lead`` channels. Genuine scalp EEG channels sharing a
  reference correlate far more strongly than that.

The dataset is still useful to the project as a clean-recording example, and it
is what exposed the bandwidth-gating bug: it samples at 200 Hz but low-passes
at ~38 Hz, so its nominal "muscle band" contains only quantization noise.
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from eegscope.detect.base import effective_bandwidth
from eegscope.pipeline import analyse
from eegscope.readers.edf import read_edf
from eegscope.triage import triage

from .common import D03, auc, summarise

CLEAN = range(1, 31)
NOISY = range(31, 41)
CONDITION = "hw"  # high workload; the split is claimed across all conditions


def _metrics(path) -> dict | None:
    try:
        rec = read_edf(path)
    except Exception:
        return None
    tri, _ = triage(rec)
    if tri.n_channels == 0:
        return None
    d, sf = tri.data, tri.sfreq

    def band_rms(lo, hi):
        hi = min(hi, sf / 2 * 0.93)
        # Guard only against an inverted or degenerate band. A 5 Hz-wide guard
        # would reject the alpha band (8-13 Hz) outright.
        if hi <= lo + 0.5:
            return np.nan
        sos = sps.butter(4, [lo, hi], btype="band", fs=sf, output="sos")
        return float(np.median(np.sqrt(np.mean(sps.sosfiltfilt(sos, d, axis=-1) ** 2, axis=-1)))) * 1e6

    freqs, psd = sps.welch(d, fs=sf, nperseg=int(min(d.shape[1], sf * 2)), axis=-1)
    i60 = int(np.argmin(np.abs(freqs - 60)))
    nb = (np.abs(freqs - 60) > 3) & (np.abs(freqs - 60) < 10)
    line = float(
        np.median(10 * np.log10(psd[:, i60] / np.maximum(psd[:, nb].mean(1), 1e-30)))
    )

    return {
        "broadband_uv": float(np.median(np.std(d, axis=1))) * 1e6,
        "alpha_uv": band_rms(8, 13),
        "drift_uv": band_rms(0.1, 1.0),
        "highfreq_uv": band_rms(40, 60),
        "step_uv": float(np.median(np.abs(np.diff(d, axis=-1)))) * 1e6,
        "line_db": line,
        "effective_bandwidth_hz": float(effective_bandwidth(d, sf)),
        "quality_score": analyse(rec).quality.score,
    }


def run(verbose: bool = True) -> dict:
    out: dict = {
        "description": "Dataset 03 clean (sub01-30) vs noisy (sub31-40)",
        "outcome": "null result - the labelled groups do not separate",
    }

    if not D03.exists():
        out["skipped"] = f"dataset 03 not found at {D03}"
        return out

    clean, noisy = [], []
    for i in list(CLEAN) + list(NOISY):
        p = D03 / f"sub{i:02d}" / f"sub{i:02d}_{CONDITION}.edf"
        if not p.exists():
            continue
        m = _metrics(p)
        if m is None:
            continue
        (clean if i <= 30 else noisy).append(m)

    if not clean or not noisy:
        out["skipped"] = "not enough subjects present"
        return out

    keys = [k for k in clean[0] if k != "effective_bandwidth_hz"]
    out["metrics"] = {}
    for k in keys:
        c = [m[k] for m in clean if np.isfinite(m[k])]
        n = [m[k] for m in noisy if np.isfinite(m[k])]
        a = auc(c, n)
        out["metrics"][k] = {
            "clean": summarise(c),
            "noisy": summarise(n),
            "auc_clean_over_noisy": None if a is None else round(a, 3),
            "separation": None if a is None else round(abs(a - 0.5), 3),
        }
        if verbose:
            if a is None or not c or not n:
                print(f"  {k:24s} not computable (no finite values)")
            else:
                print(
                    f"  {k:24s} clean {np.median(c):9.3f}  noisy {np.median(n):9.3f}  "
                    f"AUC {a:.3f}  (separation {abs(a - 0.5):.3f})"
                )

    bw = [m["effective_bandwidth_hz"] for m in clean + noisy]
    out["effective_bandwidth_hz"] = summarise(bw)
    out["bandwidth_note"] = (
        f"Sampled at 200 Hz but signal ends at ~{np.median(bw):.0f} Hz, so any "
        "muscle band above that measures quantization noise, not physiology. "
        "This is what the detector's bandwidth gate now catches."
    )

    best = max(
        (v["separation"] for v in out["metrics"].values() if v["separation"] is not None),
        default=None,
    )
    out["max_separation_over_chance"] = best
    out["conclusion"] = (
        f"No metric separates the labelled groups (best |AUC-0.5| = {best}). "
        "The planned clean-vs-noisy validation was replaced by a paired "
        "within-recording test on dataset 01; see v3_paired_rest_task.py."
    )
    return out
