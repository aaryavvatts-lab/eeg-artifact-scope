"""Pure-Python EDF / EDF+ / BDF reader.

Exists because the browser build cannot use MNE. ``tests/test_parity.py``
asserts this produces the same samples as ``mne.io.read_raw_edf``.

Format reference: Kemp et al. (1992) for EDF, BioSemi's 24-bit BDF variant,
and the EDF+ annotation (TAL) extension.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import numpy as np

from ..recording import Recording, guess_channel_type

_HEADER_BYTES = 256

# Physical-dimension string -> multiplier into volts.
_UNIT_SCALE = {
    "v": 1.0,
    "mv": 1e-3,
    "uv": 1e-6,
    "µv": 1e-6,
    "μv": 1e-6,
    "nv": 1e-9,
}


@dataclass
class Annotation:
    onset: float
    duration: float
    description: str


class EDFError(ValueError):
    pass


def _ascii(buf: bytes) -> str:
    return buf.decode("latin-1").strip()


def _int(buf: bytes, what: str) -> int:
    s = _ascii(buf)
    try:
        return int(s)
    except ValueError as exc:
        raise EDFError(f"bad integer for {what}: {s!r}") from exc


def _float(buf: bytes, what: str) -> float:
    s = _ascii(buf).replace(",", ".")
    try:
        return float(s)
    except ValueError as exc:
        raise EDFError(f"bad float for {what}: {s!r}") from exc


def _is_annotation_label(label: str) -> bool:
    return "annotation" in label.lower().replace(" ", "")


def _parse_tals(raw: bytes) -> list[Annotation]:
    """Parse EDF+ Time-stamped Annotation Lists from one channel's bytes."""
    out: list[Annotation] = []
    for block in raw.split(b"\x00"):
        if not block.strip():
            continue
        try:
            text = block.decode("utf-8", errors="replace")
        except Exception:  # pragma: no cover - defensive
            continue
        # onset[\x15duration]\x14description\x14[description...]
        parts = text.split("\x14")
        if len(parts) < 2:
            continue
        head = parts[0]
        if "\x15" in head:
            onset_s, dur_s = head.split("\x15", 1)
        else:
            onset_s, dur_s = head, "0"
        try:
            onset = float(onset_s)
            duration = float(dur_s) if dur_s.strip() else 0.0
        except ValueError:
            continue
        for desc in parts[1:]:
            desc = desc.strip()
            if desc:
                out.append(Annotation(onset, duration, desc))
    return out


def read_edf(path_or_bytes, *, exclude_annotations: bool = True) -> Recording:
    """Read an EDF/EDF+/BDF file into a :class:`Recording`.

    Parameters
    ----------
    path_or_bytes
        Filesystem path, or the raw file contents. Bytes are accepted so the
        browser can hand over an uploaded ``File`` without touching a disk.
    exclude_annotations
        Drop the EDF+ annotation channel from ``data`` (it holds text, not
        signal). Parsed annotations are always kept in ``meta['annotations']``.
    """
    if isinstance(path_or_bytes, (bytes, bytearray, memoryview)):
        buf = bytes(path_or_bytes)
    else:
        with open(path_or_bytes, "rb") as fh:
            buf = fh.read()

    if len(buf) < _HEADER_BYTES:
        raise EDFError(f"file too short to be EDF ({len(buf)} bytes)")

    head = buf[:_HEADER_BYTES]

    # BDF files start with 0xFF then "BIOSEMI"; EDF starts with "0       ".
    is_bdf = head[0] == 0xFF
    bytes_per_sample = 3 if is_bdf else 2

    n_records = _int(head[236:244], "number of records")
    record_duration = _float(head[244:252], "record duration")
    n_signals = _int(head[252:256], "number of signals")

    if n_signals <= 0:
        raise EDFError(f"no signals declared (ns={n_signals})")
    if record_duration <= 0:
        raise EDFError(f"non-positive record duration: {record_duration}")

    # Signal header: each field is stored as ns consecutive fixed-width entries.
    pos = _HEADER_BYTES

    def take(width: int) -> list[bytes]:
        nonlocal pos
        need = width * n_signals
        if pos + need > len(buf):
            raise EDFError("truncated signal header")
        chunk = buf[pos : pos + need]
        pos += need
        return [chunk[i * width : (i + 1) * width] for i in range(n_signals)]

    labels = [_ascii(b) for b in take(16)]
    take(80)  # transducer type, unused
    units = [_ascii(b) for b in take(8)]
    phys_min = np.array([_float(b, "physical min") for b in take(8)])
    phys_max = np.array([_float(b, "physical max") for b in take(8)])
    dig_min = np.array([_float(b, "digital min") for b in take(8)])
    dig_max = np.array([_float(b, "digital max") for b in take(8)])
    take(80)  # prefiltering, unused
    n_samps = np.array([_int(b, "samples per record") for b in take(8)])
    take(32)  # reserved

    data_start = pos
    record_size = int(n_samps.sum()) * bytes_per_sample
    if record_size == 0:
        raise EDFError("all signals declare zero samples per record")

    # n_records is -1 in files written without a known length; infer it.
    available = (len(buf) - data_start) // record_size
    if n_records <= 0:
        n_records = available
    elif available < n_records:
        # Truncated file: read what is actually present rather than failing.
        n_records = available
    if n_records <= 0:
        raise EDFError("no complete data records present")

    body = buf[data_start : data_start + n_records * record_size]

    # Decode the whole body once, then slice per signal.
    if is_bdf:
        raw = np.frombuffer(body, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        flat = raw[:, 0] | (raw[:, 1] << 8) | (raw[:, 2] << 16)
        flat = np.where(flat >= 1 << 23, flat - (1 << 24), flat)
    else:
        flat = np.frombuffer(body, dtype="<i2").astype(np.int32)

    flat = flat.reshape(n_records, -1)
    offsets = np.concatenate([[0], np.cumsum(n_samps)])

    annotations: list[Annotation] = []
    ann_idx = {i for i, lab in enumerate(labels) if _is_annotation_label(lab)}

    if ann_idx:
        # Annotation channels hold bytes, not samples; re-extract them raw.
        byte_off = np.concatenate([[0], np.cumsum(n_samps * bytes_per_sample)])
        for i in sorted(ann_idx):
            chunks = []
            for r in range(n_records):
                s = r * record_size + int(byte_off[i])
                e = s + int(n_samps[i]) * bytes_per_sample
                chunks.append(body[s:e])
            annotations.extend(_parse_tals(b"".join(chunks)))

    keep = [i for i in range(n_signals) if not (exclude_annotations and i in ann_idx)]
    if not keep:
        raise EDFError("no signal channels left after excluding annotations")

    # Channels may declare different sample counts. Keep the modal rate and
    # report the rest rather than silently resampling into a wrong timebase.
    modal = int(np.bincount(n_samps[keep]).argmax())
    dropped_rate = [labels[i] for i in keep if int(n_samps[i]) != modal]
    keep = [i for i in keep if int(n_samps[i]) == modal]
    if not keep:
        raise EDFError("no channels share a common sample rate")

    n_samples = modal * n_records
    out = np.empty((len(keep), n_samples), dtype=np.float64)

    blank_unit_channels: list[str] = []

    for row, i in enumerate(keep):
        s, e = int(offsets[i]), int(offsets[i + 1])
        digital = flat[:, s:e].reshape(-1)
        span = dig_max[i] - dig_min[i]
        if span == 0:
            out[row] = 0.0
            continue
        gain = (phys_max[i] - phys_min[i]) / span
        physical = (digital - dig_min[i]) * gain + phys_min[i]
        unit = units[i].strip().lower()
        if unit in _UNIT_SCALE:
            scale = _UNIT_SCALE[unit]
        elif not unit:
            # Blank physical dimension violates the EDF spec but is common in
            # consumer-hardware exports (all of dataset 01 does it). Microvolts
            # is the overwhelming EEG convention, and it is the only reading
            # that yields physically possible amplitudes -- interpreting these
            # as volts would imply +/-175 V at the scalp. MNE assumes volts
            # here, so our values differ from it by 1e6 on such files by design.
            scale = 1e-6
            blank_unit_channels.append(labels[i])
        else:
            scale = 1.0
        out[row] = physical * scale

    sfreq = modal / record_duration
    names = [labels[i] for i in keep]
    types = [guess_channel_type(n) for n in names]

    meta = {
        "annotations": annotations,
        "units": [units[i] for i in keep],
        "n_records": n_records,
        "record_duration": record_duration,
        "subject": _ascii(head[8:88]),
        "recording": _ascii(head[88:168]),
        "startdate": _ascii(head[168:176]),
        "starttime": _ascii(head[176:184]),
    }
    if dropped_rate:
        meta["dropped_mixed_rate_channels"] = dropped_rate
    if blank_unit_channels:
        meta["assumed_microvolts"] = blank_unit_channels

    # Recorded so triage can warn when the unit guess yields implausible
    # amplitudes (healthy scalp EEG sits well under a few mV).
    eeg_rows = [r for r, i in enumerate(keep) if guess_channel_type(labels[i]) == "eeg"]
    if eeg_rows:
        meta["median_abs_amplitude_v"] = float(np.median(np.abs(out[eeg_rows])))

    return Recording(
        data=out,
        sfreq=sfreq,
        ch_names=names,
        ch_types=types,
        source_format="bdf" if is_bdf else "edf",
        meta=meta,
    )


def sniff_is_edf(head: bytes) -> bool:
    """Cheap magic-byte check used by the format dispatcher."""
    if len(head) < 8:
        return False
    if head[0] == 0xFF and b"BIOSEMI" in head[:16]:
        return True
    return bool(re.match(rb"^0\s{7}", head[:8]))
