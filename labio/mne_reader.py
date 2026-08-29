"""MNE-backed reading, for formats ``eegscope`` deliberately does not carry.

``eegscope`` stays limited to numpy/scipy/sklearn so it can run in Pyodide.
That rules out `.fif`, BrainVision and full BIDS trees, whose readers are large
and format-specific. Offline there is no such constraint, so the CLI falls back
here and hands the result to the same detectors.

This module is also the reference implementation ``tests/test_parity.py``
checks the dependency-free readers against.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from eegscope.recording import Recording

# MNE channel kinds -> our vocabulary.
_TYPE_MAP = {
    "eeg": "eeg",
    "eog": "eog",
    "ecg": "ecg",
    "emg": "emg",
    "misc": "misc",
    "stim": "misc",
    "seeg": "eeg",
    "ecog": "eeg",
}


def read_with_mne(path: str | Path, *, preload: bool = True) -> Recording:
    """Read anything MNE can open into a :class:`Recording`."""
    import mne

    mne.set_log_level("ERROR")
    path = Path(path)

    raw = mne.io.read_raw(path, preload=preload, verbose="ERROR")
    return from_mne_raw(raw, source_format=f"mne:{path.suffix.lstrip('.') or 'unknown'}")


def from_mne_raw(raw, source_format: str = "mne") -> Recording:
    """Convert an ``mne.io.Raw`` into a :class:`Recording`.

    MNE already returns volts, which is what ``Recording`` expects, so no
    rescaling happens here.
    """
    import mne

    types = raw.get_channel_types()
    mapped = [_TYPE_MAP.get(t, "misc") for t in types]

    annotations = []
    if raw.annotations is not None and len(raw.annotations):
        from eegscope.readers.edf import Annotation

        for a in raw.annotations:
            annotations.append(
                Annotation(
                    onset=float(a["onset"]),
                    duration=float(a["duration"]),
                    description=str(a["description"]),
                )
            )

    data = np.asarray(raw.get_data(), dtype=np.float64)
    meta = {
        "annotations": annotations,
        "mne_info": {
            "highpass": float(raw.info.get("highpass") or 0.0),
            "lowpass": float(raw.info.get("lowpass") or 0.0),
            "line_freq": raw.info.get("line_freq"),
        },
    }
    eeg_rows = [i for i, t in enumerate(mapped) if t == "eeg"]
    if eeg_rows:
        meta["median_abs_amplitude_v"] = float(np.median(np.abs(data[eeg_rows])))

    return Recording(
        data=data,
        sfreq=float(raw.info["sfreq"]),
        ch_names=list(raw.ch_names),
        ch_types=mapped,
        source_format=source_format,
        meta=meta,
    )


def read_bids(root: str | Path, subject: str, task: str | None = None) -> Recording:
    """Read one BIDS EEG run via ``mne-bids``."""
    from mne_bids import BIDSPath, read_raw_bids

    bp = BIDSPath(subject=subject, task=task, root=str(root), datatype="eeg")
    matches = bp.match()
    if not matches:
        raise FileNotFoundError(f"no BIDS EEG run for sub-{subject} task-{task} in {root}")
    raw = read_raw_bids(matches[0], verbose="ERROR")
    raw.load_data()
    return from_mne_raw(raw, source_format="mne:bids")
