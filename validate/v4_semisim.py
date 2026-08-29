"""V4 - Detection of a known injected ocular artifact (dataset 04).

**Reduced scope, for a reason outside our control.** The plan was to compare a
cleaned signal against ``Pure_Data.mat``, the pre-contamination ground truth.
That file cannot be recovered: the published archive is corrupt.

    archive declares : Contaminated 28,330,804 + HEOG 1,198,492
                       + Pure_Data 22,924,611  = 52,453,907 bytes
    archive actually : 46,757,186 bytes  (matches Mendeley's published size,
                       so the download is complete -- the hosted file is short)
    7-Zip verdict    : ERROR: CRC Failed : Pure_Data.mat
                       (17,261,114 of 22,924,611 bytes present)

Both libarchive and 7-Zip 25.01 fail identically, so this is the archive rather
than the tooling.

**The artifact here is not a blink.** Measured on the intact HEOG traces, 86%
of their power sits in 0.1-1 Hz and each ~28 s segment contains only 2-4
excursions. That is *horizontal eye movement* -- slow lateral deflection --
whereas a blink is a fast 1-10 Hz triphasic event. Scoring a blink detector
against it would be measuring the wrong thing and would report a low number as
if it were a failure.

So this validates what the data actually supports: given EEG contaminated by a
known ocular artifact at known times, does the pipeline flag those times *at
all*, and which detector does the catching?
"""

from __future__ import annotations

import numpy as np
from scipy import signal as sps

from eegscope.detect.base import BLINK, DRIFT
from eegscope.detect.blink import detect_blinks
from eegscope.detect.drift import detect_drift
from eegscope.recording import Recording

from .common import D04, summarise

# The dataset ships no sampling rate; its publication describes 200 Hz, and the
# segment lengths (5401-8401 samples) match the ~27-42 s epochs that implies.
ASSUMED_SFREQ = 200.0

MONTAGE_19 = [
    "Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8",
    "T3", "C3", "Cz", "C4", "T4",
    "T5", "P3", "Pz", "P4", "T6",
    "O1", "O2",
]

# Where the injected artifact actually lives (86% of HEOG power).
OCULAR_BAND = (0.1, 1.0)
TOLERANCE_S = 1.5
GROUND_TRUTH_MAD = 4.0


def _heog_events(heog: np.ndarray, sfreq: float) -> list[float]:
    """Times of genuine horizontal eye movements in the HEOG trace."""
    sos = sps.butter(2, OCULAR_BAND, btype="band", fs=sfreq, output="sos")
    envelope = np.abs(sps.hilbert(sps.sosfiltfilt(sos, heog)))

    win = max(3, int(1.0 * sfreq) | 1)
    kernel = sps.windows.hann(win)
    kernel /= kernel.sum()
    envelope = np.convolve(envelope, kernel, mode="same")

    med = np.median(envelope)
    mad = np.median(np.abs(envelope - med)) * 1.4826
    if mad <= 0:
        return []
    peaks, _ = sps.find_peaks(
        (envelope - med) / mad, height=GROUND_TRUTH_MAD, distance=int(1.5 * sfreq)
    )
    return list(peaks / sfreq)


def _covered(t: float, spans: list[tuple[float, float]], tol: float) -> bool:
    return any(lo - tol <= t <= hi + tol for lo, hi in spans)


def run(verbose: bool = True) -> dict:
    out: dict = {
        "description": (
            "Does the pipeline flag EEG at times where a known ocular artifact "
            "was injected?"
        ),
        "scope_note": (
            "Reduced from the planned cleaning-fidelity test: the published "
            "archive is corrupt and Pure_Data.mat fails CRC (17.3 MB of "
            "22.9 MB present). Contaminated_Data.mat and HEOG.mat are intact."
        ),
        "artifact_note": (
            "The injected artifact is horizontal eye movement, not blinks: 86% "
            "of HEOG power sits in 0.1-1 Hz and each segment holds only 2-4 "
            "excursions. Recall is therefore reported for the pipeline overall "
            "and broken down by detector, rather than scored against the blink "
            "detector alone."
        ),
        "assumed_sfreq_hz": ASSUMED_SFREQ,
        "tolerance_s": TOLERANCE_S,
    }

    con_path = D04 / "Contaminated_Data.mat"
    heog_path = D04 / "HEOG.mat"
    if not con_path.exists() or not heog_path.exists():
        out["skipped"] = f"dataset 04 files not found in {D04}"
        return out

    from scipy.io import loadmat

    con = loadmat(con_path)
    heo = loadmat(heog_path)

    sims = sorted(
        (k for k in con if k.startswith("sim") and k.endswith("_con")),
        key=lambda k: int(k[3:-4]),
    )

    recall_any, recall_drift, recall_blink = [], [], []
    n_truth_total = 0

    for key in sims:
        idx = key[3:-4]
        hk = f"heog_{idx}"
        if hk not in heo:
            continue

        data = np.asarray(con[key], dtype=float)
        heog = np.asarray(heo[hk], dtype=float).ravel()
        if data.shape[1] != heog.size:
            continue

        truth = _heog_events(heog, ASSUMED_SFREQ)
        if not truth:
            continue
        n_truth_total += len(truth)

        names = (
            MONTAGE_19
            if data.shape[0] == len(MONTAGE_19)
            else [f"ch{i + 1}" for i in range(data.shape[0])]
        )
        rec = Recording(
            data=data * 1e-6,  # values are microvolts
            sfreq=ASSUMED_SFREQ,
            ch_names=names,
            ch_types=["eeg"] * data.shape[0],
            source_format="semisim",
        )

        d_res = detect_drift(rec)
        b_res = detect_blinks(rec)
        d_spans = [(e.onset, e.offset) for e in d_res.events] if d_res.ok else []
        b_spans = [(e.onset, e.offset) for e in b_res.events] if b_res.ok else []
        both = d_spans + b_spans

        recall_any.append(
            np.mean([_covered(t, both, TOLERANCE_S) for t in truth])
        )
        recall_drift.append(
            np.mean([_covered(t, d_spans, TOLERANCE_S) for t in truth])
        )
        recall_blink.append(
            np.mean([_covered(t, b_spans, TOLERANCE_S) for t in truth])
        )

    out["n_simulations"] = len(recall_any)
    out["n_injected_artifacts"] = n_truth_total
    out["recall_any_detector"] = summarise(recall_any)
    out["recall_drift_detector"] = summarise(recall_drift)
    out["recall_blink_detector"] = summarise(recall_blink)

    if verbose:
        print(
            f"  {len(recall_any)} simulations, {n_truth_total} injected artifacts"
        )
        print(f"    recall (any detector)   {out['recall_any_detector']['mean']}")
        print(f"    recall (drift detector) {out['recall_drift_detector']['mean']}")
        print(f"    recall (blink detector) {out['recall_blink_detector']['mean']}")
    return out
