"""Export real recordings into small JSON files the website can draw.

Everything the site shows comes from here. Nothing on the page is invented or
drawn from made-up numbers, so if a figure looks wrong it can be traced back to
a specific file and time range in the datasets.

    python -m validate.export_site_data
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy import signal as sps

from eegscope.detect.base import robust_z
from eegscope.detect.blink import detect_blinks
from eegscope.readers.edf import read_edf
from eegscope.triage import triage, virtual_eog_index

from .common import DEVICES, D01_SOURCE, ROOT, beep_times

OUT = ROOT / "web" / "public" / "data"

# Keep the payload small. The page is at most ~1200 px wide, so more points
# than this buy nothing.
TRACE_POINTS = 600
PSD_POINTS = 140
MAX_SNIPPET_CHANNELS = 3


def _decimate_minmax(x: np.ndarray, points: int) -> list[list[float]]:
    """Min/max per bucket, so a short spike survives downsampling."""
    n = x.size
    if n <= points * 2:
        return [[round(float(v), 3), round(float(v), 3)] for v in x]
    edges = np.linspace(0, n, points + 1, dtype=int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = x[a : max(b, a + 1)]
        out.append([round(float(seg.min()), 3), round(float(seg.max()), 3)])
    return out


def _resample_to(x: np.ndarray, n: int) -> list[float]:
    idx = np.linspace(0, x.size - 1, n)
    return [round(float(v), 3) for v in np.interp(idx, np.arange(x.size), x)]


# ---------------------------------------------------------------- blink shape


def blink_shapes() -> dict:
    """Average blink waveform per device, on a shared time axis.

    Built by averaging real detected blinks, so the shape is what the hardware
    actually recorded rather than a drawing of what a blink is meant to be.
    """
    window_s = 1.4
    n_points = 180
    out: dict = {"window_s": window_s, "n_points": n_points, "devices": {}}

    for dev, meta in DEVICES.items():
        stacks: list[np.ndarray] = []
        rest_rms: list[float] = []
        chan_name = "?"

        for i in range(1, 16):
            sub = f"sub-{i:02d}"
            path = D01_SOURCE / sub / f"{sub}_task-EB_acq-{dev}_eeg.edf"
            if not path.exists():
                continue
            rec = read_edf(path)
            tri, _ = triage(rec)
            if not tri.n_channels:
                continue

            beeps = beep_times(rec)
            if len(beeps) != 20:
                continue

            res = detect_blinks(tri)
            if not res.events:
                continue

            # Use the most frontal electrode, not whichever channel happens to
            # show the largest swing. On the dry-electrode DSI-24 the noisiest
            # channel is often temporal (T4), and picking by size would plot
            # electrode noise instead of the blink.
            frontal = virtual_eog_index(tri)
            if not frontal:
                continue
            ch = frontal[0]
            sig = tri.data[ch] * 1e6

            half = int(window_s / 2 * tri.sfreq)
            for e in res.events:
                c = int((e.onset + e.duration / 2) * tri.sfreq)
                if c - half < 0 or c + half >= sig.size:
                    continue
                seg = sig[c - half : c + half]
                # Centre each blink on its own baseline before averaging.
                stacks.append(_resample_to(seg - np.median(seg), n_points))

            chan_name = tri.ch_names[ch]
            rest = tri.crop(0.0, max(5.0, beeps[0] - 5.0)).data[ch] * 1e6
            rest_rms.append(float(np.std(rest)))

        if not stacks:
            continue

        arr = np.asarray(stacks, dtype=float)
        # Blink polarity flips with the reference montage, so align each blink
        # to the sign of its own largest deflection before averaging. Without
        # this, opposite-polarity blinks cancel into a flat line.
        peak_idx = np.abs(arr).argmax(axis=1)
        signs = np.sign(arr[np.arange(arr.shape[0]), peak_idx])
        signs[signs == 0] = 1.0
        arr = arr * signs[:, None]

        mean = arr.mean(axis=0)
        out["devices"][dev] = {
            "label": meta["label"],
            "channel": chan_name,
            "tier": meta["tier"],
            "channels": meta["channels"],
            "n_blinks": int(arr.shape[0]),
            "mean": [round(float(v), 2) for v in mean],
            "p25": [round(float(v), 2) for v in np.percentile(arr, 25, axis=0)],
            "p75": [round(float(v), 2) for v in np.percentile(arr, 75, axis=0)],
            "peak_uv": round(float(np.abs(mean).max()), 1),
            "rest_rms_uv": round(float(np.mean(rest_rms)), 2) if rest_rms else None,
        }

    return out


# ------------------------------------------------------------ real snippets


def _snippet(path: Path, t0: float, t1: float, label: str, note: str) -> dict | None:
    if not path.exists():
        return None
    rec = read_edf(path)
    tri, _ = triage(rec)
    if not tri.n_channels:
        return None
    seg = tri.crop(t0, t1)

    chans = []
    for i, name in enumerate(seg.ch_names[:MAX_SNIPPET_CHANNELS]):
        chans.append(
            {"name": name, "minmax": _decimate_minmax(seg.data[i] * 1e6, TRACE_POINTS)}
        )

    freqs, psd = sps.welch(
        seg.data, fs=seg.sfreq, nperseg=int(min(seg.n_samples, seg.sfreq * 2)), axis=-1
    )
    keep = freqs <= min(seg.sfreq / 2, 120.0)
    f, p = freqs[keep], psd.mean(axis=0)[keep]
    if f.size > PSD_POINTS:
        idx = np.unique(np.linspace(0, f.size - 1, PSD_POINTS).astype(int))
        f, p = f[idx], p[idx]

    return {
        "label": label,
        "note": note,
        "source": path.name,
        "t0": t0,
        "t1": t1,
        "sfreq": seg.sfreq,
        "duration_s": round(seg.duration, 2),
        "channels": chans,
        "psd": {
            "freqs": [round(float(v), 2) for v in f],
            "db": [round(float(10 * np.log10(max(v * 1e12, 1e-12))), 2) for v in p],
        },
        "peak_uv": round(float(np.abs(seg.data).max() * 1e6), 1),
        "rms_uv": round(float(np.std(seg.data) * 1e6), 2),
    }


def artifact_examples() -> dict:
    """Matched rest and artifact windows from the same subject and device."""
    sub = "sub-01"
    out: dict = {"description": "Same subject, same headset, rest vs cued artifact", "items": []}

    plan = [
        ("DSI", "EB", 5.0, 35.0, "Resting, research headset",
         "DSI-24, no task. This is what the tool should call clean."),
        ("DSI", "EB", 64.0, 94.0, "Blinking on cue, research headset",
         "Same electrode, same person, one minute later. Blinks every three seconds."),
        ("DSI", "BT", 64.0, 94.0, "Clenching the jaw, research headset",
         "Fast, broadband, and strongest at the temples. This is the one that ruins a recording."),
        ("Muse2", "EB", 5.0, 35.0, "Resting, consumer headband",
         "Muse 2. Four electrodes, two of them just above the eyebrows."),
        ("Muse2", "EB", 64.0, 94.0, "Blinking on cue, consumer headband",
         "AF7 and AF8 sit right over the eyes, so a blink lands square on them."),
        ("MW2", "EB", 64.0, 94.0, "Blinking on cue, single electrode",
         "One electrode at Fp1. There is no other channel to cross-check against."),
    ]

    for dev, task, t0, t1, label, note in plan:
        path = D01_SOURCE / sub / f"{sub}_task-{task}_acq-{dev}_eeg.edf"
        item = _snippet(path, t0, t1, label, note)
        if item:
            item["device"] = DEVICES[dev]["label"]
            item["device_key"] = dev
            item["condition"] = task
            out["items"].append(item)

    return out


# ---------------------------------------------------------- threshold sweep


def threshold_sweep() -> dict:
    """How recall and over-counting trade off as the blink threshold moves.

    This is the calibration that set the shipped default, re-run so the page
    can show the curve instead of asserting the number.
    """
    thresholds = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0]
    out: dict = {
        "thresholds": thresholds,
        "shipped_default": 4.0,
        "note": (
            "Recall is the share of cued blinks found. Detections per cue near "
            "1.0 means one detection per blink, which is what a rate estimate "
            "needs. Rest rate is detections per minute while the subject was "
            "told to sit still."
        ),
        "devices": {},
    }

    subjects = [f"sub-{i:02d}" for i in range(1, 16)]

    for dev, meta in DEVICES.items():
        recall, per_cue, rest_rate = [], [], []
        n_files = 0
        cached = []
        for sub in subjects:
            path = D01_SOURCE / sub / f"{sub}_task-EB_acq-{dev}_eeg.edf"
            if not path.exists():
                continue
            rec = read_edf(path)
            beeps = beep_times(rec)
            if len(beeps) != 20:
                continue
            tri, _ = triage(rec)
            if tri.n_channels:
                cached.append((rec, tri, beeps))
        n_files = len(cached)

        for z in thresholds:
            r_vals, c_vals, rest_vals = [], [], []
            for rec, tri, beeps in cached:
                res = detect_blinks(tri, z_threshold=z)
                times = [e.onset for e in res.events]
                lo, hi = beeps[0] - 1.0, beeps[-1] + 3.0
                hits = sum(any(b - 0.3 <= t <= b + 2.0 for t in times) for b in beeps)
                in_task = sum(1 for t in times if lo <= t <= hi)
                rest_span = rec.duration - (hi - lo)
                rest_n = len(times) - in_task
                r_vals.append(hits / len(beeps))
                c_vals.append(in_task / len(beeps))
                rest_vals.append(rest_n / (rest_span / 60.0) if rest_span > 0 else 0.0)
            recall.append(round(float(np.mean(r_vals)), 4) if r_vals else None)
            per_cue.append(round(float(np.mean(c_vals)), 4) if c_vals else None)
            rest_rate.append(round(float(np.mean(rest_vals)), 3) if rest_vals else None)

        out["devices"][dev] = {
            "label": meta["label"],
            "n_files": n_files,
            "recall": recall,
            "detections_per_cue": per_cue,
            "rest_per_minute": rest_rate,
        }

    return out


# --------------------------------------------------------- bandwidth demo


def bandwidth_demo() -> dict:
    """Spectra showing why sample rate is not the same as usable bandwidth."""
    from .common import D03

    out: dict = {
        "description": (
            "Average spectrum, normalised to each recording's own level at "
            "10 Hz. A sharp drop means the system filtered that band away, so "
            "anything measured above it is noise rather than physiology."
        ),
        "items": [],
    }

    plan = [
        (D03 / "sub01" / "sub01_hw.edf", "Clinical system, 200 Hz",
         "Sampled at 200 Hz but nothing survives past about 38 Hz."),
        (D01_SOURCE / "sub-01" / "sub-01_task-BT_acq-DSI_eeg.edf", "DSI-24, 300 Hz",
         "Real content all the way up. The spike at 60 Hz is mains hum."),
        (D01_SOURCE / "sub-01" / "sub-01_task-BT_acq-MW2_eeg.edf", "MindWave 2, 512 Hz",
         "Widest usable band of the four headsets."),
    ]

    for path, label, note in plan:
        if not path.exists():
            continue
        rec = read_edf(path)
        tri, _ = triage(rec)
        if not tri.n_channels:
            continue
        freqs, psd = sps.welch(
            tri.data, fs=tri.sfreq, nperseg=int(min(tri.n_samples, tri.sfreq * 2)), axis=-1
        )
        mean = psd.mean(axis=0)
        ref = mean[int(np.argmin(np.abs(freqs - 10.0)))]
        db = 10 * np.log10(np.maximum(mean / max(ref, 1e-30), 1e-9))
        keep = freqs <= min(tri.sfreq / 2, 160.0)
        f, d = freqs[keep], db[keep]
        if f.size > PSD_POINTS:
            idx = np.unique(np.linspace(0, f.size - 1, PSD_POINTS).astype(int))
            f, d = f[idx], d[idx]

        from eegscope.detect.base import effective_bandwidth

        out["items"].append(
            {
                "label": label,
                "note": note,
                "sfreq": tri.sfreq,
                "effective_bandwidth_hz": round(float(effective_bandwidth(tri.data, tri.sfreq)), 1),
                "freqs": [round(float(v), 2) for v in f],
                "db": [round(float(v), 2) for v in d],
            }
        )

    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    jobs = [
        ("blink-shapes.json", blink_shapes),
        ("artifact-examples.json", artifact_examples),
        ("threshold-sweep.json", threshold_sweep),
        ("bandwidth.json", bandwidth_demo),
    ]

    for name, fn in jobs:
        print(f"building {name} ...", flush=True)
        data = fn()
        path = OUT / name
        path.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        print(f"  wrote {path.relative_to(ROOT)}  ({path.stat().st_size / 1024:.0f} KB)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
