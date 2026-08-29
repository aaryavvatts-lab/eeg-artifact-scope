"""Adapter between the analysis and the browser UI.

Returns a compact JSON payload: the report, plus decimated traces for drawing.
Decimation matters -- a 50-minute 70-channel recording is ~200 million samples,
and serialising that into JavaScript would exhaust memory for a plot that is
1200 pixels wide.
"""

from __future__ import annotations

import json

import numpy as np
from scipy import signal as sps

from .pipeline import analyse

# Plot resolution targets. A trace wider than the screen buys nothing.
PREVIEW_POINTS = 2000
PSD_POINTS = 220
MAX_PREVIEW_CHANNELS = 24


def _minmax_decimate(x: np.ndarray, points: int) -> list[list[float]]:
    """Decimate to ``points`` min/max pairs.

    Plain subsampling would drop the very spikes this tool exists to show: a
    2 ms electrode pop falls between samples. Keeping the min and max of each
    bucket preserves the envelope, so an artifact stays visible at any zoom.
    """
    n = x.size
    if n <= points * 2:
        return [[float(v), float(v)] for v in x]
    edges = np.linspace(0, n, points + 1, dtype=int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            b = a + 1
        seg = x[a:b]
        out.append([float(seg.min()), float(seg.max())])
    return out


def analyse_for_web(source, filename: str | None = None) -> str:
    """Run the pipeline and return a JSON string for the UI."""
    analysis = analyse(source, filename=filename)
    payload = analysis.as_dict()

    rec = analysis.triaged if analysis.triaged.n_channels else analysis.recording

    if rec.n_channels:
        # Show the most informative channels first when there are many.
        order = list(range(rec.n_channels))[:MAX_PREVIEW_CHANNELS]
        payload["preview"] = {
            "duration_s": round(rec.duration, 3),
            "sfreq": rec.sfreq,
            "n_shown": len(order),
            "n_total": rec.n_channels,
            "channels": [
                {
                    "name": rec.ch_names[i],
                    # Microvolts: what an EEG researcher expects to read.
                    "minmax": _minmax_decimate(rec.data[i] * 1e6, PREVIEW_POINTS),
                }
                for i in order
            ],
        }

        # Average PSD, log-spaced so low frequencies are not crushed.
        nperseg = int(min(rec.n_samples, max(rec.sfreq * 2, 256)))
        if nperseg >= 64:
            freqs, psd = sps.welch(rec.data, fs=rec.sfreq, nperseg=nperseg, axis=-1)
            mean_psd = psd.mean(axis=0)
            keep = freqs <= min(rec.sfreq / 2, 128.0)
            freqs, mean_psd = freqs[keep], mean_psd[keep]
            if freqs.size > PSD_POINTS:
                idx = np.unique(
                    np.linspace(0, freqs.size - 1, PSD_POINTS).astype(int)
                )
                freqs, mean_psd = freqs[idx], mean_psd[idx]
            payload["psd"] = {
                "freqs": [round(float(f), 3) for f in freqs],
                # dB relative to 1 uV^2/Hz.
                "db": [
                    round(float(10 * np.log10(max(v * 1e12, 1e-12))), 3)
                    for v in mean_psd
                ],
            }

    return json.dumps(payload)


def analyse_bytes(buf, filename: str | None = None) -> str:
    """Entry point the worker calls with an uploaded file's bytes."""
    return analyse_for_web(bytes(buf), filename)
