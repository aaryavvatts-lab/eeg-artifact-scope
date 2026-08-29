"""EEGLAB ``.set`` reader.

Works in the browser because these are MATLAB v5 files and ``scipy.io.loadmat``
is available in Pyodide. Files saved as MATLAB v7.3 (HDF5) are not readable
here and are reported as such rather than failing obscurely.

Channel types are the subtle part. EEGLAB's ``chanlocs.type`` is frequently
just "EEG" for every channel -- dataset 02 labels its HEOG, VEOG and two ECG
electrodes that way, so trusting it would feed eye and heart traces into the
EEG analysis. When a BIDS ``*_channels.tsv`` sits beside the file it is
authoritative and used instead.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ..recording import Recording, guess_channel_type

# EEGLAB stores samples in microvolts by convention.
_EEGLAB_UNIT_SCALE = 1e-6

# BIDS channel-type strings -> our vocabulary.
_BIDS_TYPE = {
    "EEG": "eeg",
    "EOG": "eog",
    "HEOG": "eog",
    "VEOG": "eog",
    "ECG": "ecg",
    "EKG": "ecg",
    "EMG": "emg",
    "MISC": "misc",
    "TRIG": "misc",
    "REF": "misc",
}


class EEGLABError(ValueError):
    pass


def sniff_is_matlab(head: bytes) -> bool:
    """MATLAB v5 files begin with a text description header."""
    return head[:6] == b"MATLAB"


def _read_bids_channels(set_path: Path) -> dict[str, str] | None:
    """Channel name -> type from a sibling BIDS ``*_channels.tsv``, if present."""
    stem = set_path.name
    for suffix in ("_eeg.set", ".set"):
        if stem.endswith(suffix):
            base = stem[: -len(suffix)]
            break
    else:
        return None

    candidate = set_path.parent / f"{base}_channels.tsv"
    if not candidate.exists():
        return None

    try:
        lines = candidate.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if len(lines) < 2:
        return None

    header = lines[0].split("\t")
    try:
        i_name, i_type = header.index("name"), header.index("type")
    except ValueError:
        return None

    out: dict[str, str] = {}
    for row in lines[1:]:
        parts = row.split("\t")
        if len(parts) > max(i_name, i_type):
            out[parts[i_name].strip()] = parts[i_type].strip().upper()
    return out or None


def read_set(path_or_bytes, *, channels_tsv: dict[str, str] | None = None) -> Recording:
    """Read an EEGLAB ``.set`` into a :class:`Recording`."""
    from scipy.io import loadmat  # local import keeps module import cheap

    source_path: Path | None = None
    if not isinstance(path_or_bytes, (bytes, bytearray, memoryview)):
        source_path = Path(os.fspath(path_or_bytes))

    try:
        mat = loadmat(path_or_bytes, squeeze_me=True, struct_as_record=False)
    except NotImplementedError as exc:
        raise EEGLABError(
            "This .set file is MATLAB v7.3 (HDF5), which cannot be read in the "
            "browser. Re-save it from EEGLAB as v7, or use the local "
            "command-line tool."
        ) from exc

    # EEGLAB writes either a single `EEG` struct or the fields flattened to the
    # top level, depending on version and save options. Accept both.
    if "EEG" in mat:
        eeg = mat["EEG"]
        get = lambda k, d=None: getattr(eeg, k, d)  # noqa: E731
    else:
        get = mat.get

    data = get("data")
    if data is None:
        raise EEGLABError("no `data` field found in this .set file")

    # A string here means the samples live in a companion .fdt file.
    if isinstance(data, str) or (isinstance(data, np.ndarray) and data.dtype.kind in "US"):
        fname = str(data)
        if source_path is None:
            raise EEGLABError(
                f"Samples are stored in a separate file ({fname}), which is not "
                "available. Upload the .fdt alongside the .set, or use the "
                "local command-line tool."
            )
        fdt = source_path.parent / fname
        if not fdt.exists():
            raise EEGLABError(f"companion data file not found: {fdt.name}")
        n_ch = int(get("nbchan", 0))
        raw = np.fromfile(fdt, dtype=np.float32)
        if n_ch <= 0 or raw.size % n_ch:
            raise EEGLABError(f"cannot reshape {raw.size} samples into {n_ch} channels")
        data = raw.reshape(-1, n_ch).T

    data = np.asarray(data, dtype=np.float64)
    if data.ndim == 3:
        # Epoched data: concatenate trials back into a continuous stream.
        data = data.reshape(data.shape[0], -1)
    if data.ndim != 2:
        raise EEGLABError(f"unexpected data shape {data.shape}")

    sfreq = float(get("srate", 0) or 0)
    if sfreq <= 0:
        raise EEGLABError(f"invalid sampling rate: {sfreq}")

    # -- channel names and types ------------------------------------------
    chanlocs = get("chanlocs")
    names: list[str] = []
    set_types: list[str] = []
    if chanlocs is not None:
        for c in np.atleast_1d(chanlocs):
            names.append(str(getattr(c, "labels", "")).strip())
            set_types.append(str(getattr(c, "type", "") or "").strip().upper())
    if len(names) != data.shape[0]:
        names = [f"ch{i + 1}" for i in range(data.shape[0])]
        set_types = [""] * data.shape[0]

    if channels_tsv is None and source_path is not None:
        channels_tsv = _read_bids_channels(source_path)

    types: list[str] = []
    used_sidecar = False
    for name, stype in zip(names, set_types):
        if channels_tsv and name in channels_tsv:
            mapped = _BIDS_TYPE.get(channels_tsv[name])
            if mapped:
                types.append(mapped)
                used_sidecar = True
                continue
        # chanlocs types are only useful when they actually distinguish
        # something; a file that says "EEG" for all 74 channels tells us nothing.
        mapped = _BIDS_TYPE.get(stype)
        if mapped and len(set(set_types)) > 1:
            types.append(mapped)
        else:
            types.append(guess_channel_type(name))

    meta = {
        "setname": str(get("setname", "") or ""),
        "reference": str(get("ref", "") or ""),
        "n_trials": int(get("trials", 1) or 1),
        "channel_types_from_sidecar": used_sidecar,
    }
    if not used_sidecar and len(set(set_types)) <= 1:
        meta["channel_type_warning"] = (
            "This .set labels every channel the same type, so EOG/ECG channels "
            "cannot be told apart from EEG. Place the BIDS *_channels.tsv "
            "beside the file for correct typing."
        )

    eeg_rows = [i for i, t in enumerate(types) if t == "eeg"]
    scaled = data * _EEGLAB_UNIT_SCALE
    if eeg_rows:
        meta["median_abs_amplitude_v"] = float(np.median(np.abs(scaled[eeg_rows])))

    return Recording(
        data=scaled,
        sfreq=sfreq,
        ch_names=names,
        ch_types=types,
        source_format="eeglab",
        meta=meta,
    )
