"""Minimal EDF writer.

Only used offline, to cut small excerpts out of the public datasets so the
website can offer example recordings without shipping whole studies. It writes
plain EDF (16 bit), which every EEG tool can read.

Deliberately writes a correct ``uV`` in the physical dimension field. The
originals leave it blank, which is against the specification and is one of the
things this project had to work around.
"""

from __future__ import annotations

import numpy as np

from ..recording import Recording

DIGITAL_MIN = -32768
DIGITAL_MAX = 32767


def _fixed(text: str, width: int) -> bytes:
    """ASCII, left aligned, padded or truncated to exactly ``width``."""
    raw = str(text).encode("ascii", errors="replace")[:width]
    return raw + b" " * (width - len(raw))


def _num(value: float, width: int) -> bytes:
    """A number that fits in ``width`` characters, keeping as much precision as fits."""
    for fmt in ("{:g}", "{:.6f}", "{:.3f}", "{:.1f}", "{:.0f}"):
        text = fmt.format(value)
        if len(text) <= width:
            return _fixed(text, width)
    return _fixed(text[:width], width)


def write_edf(
    rec: Recording,
    path,
    *,
    record_seconds: float = 1.0,
    patient: str = "X X X X",
    recording_id: str = "Startdate X X X X",
) -> int:
    """Write ``rec`` to ``path`` as EDF. Returns the number of bytes written.

    Samples are scaled per channel so each uses the full 16 bit range, which
    keeps quantisation error well under the noise floor of any real EEG.
    """
    data = np.asarray(rec.data, dtype=np.float64)
    n_ch = data.shape[0]
    if n_ch == 0:
        raise ValueError("nothing to write: no channels")

    samples_per_record = int(round(rec.sfreq * record_seconds))
    if samples_per_record < 1:
        raise ValueError(f"record_seconds={record_seconds} is too short for {rec.sfreq} Hz")

    n_records = int(data.shape[1] // samples_per_record)
    if n_records < 1:
        raise ValueError("recording is shorter than one data record")
    usable = n_records * samples_per_record
    data = data[:, :usable]

    # Work in microvolts, which is what the unit field will declare.
    micro = data * 1e6

    phys_min = np.empty(n_ch)
    phys_max = np.empty(n_ch)
    digital = np.empty((n_ch, usable), dtype=np.int16)

    for i in range(n_ch):
        lo = float(np.min(micro[i]))
        hi = float(np.max(micro[i]))
        if not np.isfinite(lo) or not np.isfinite(hi) or hi - lo < 1e-9:
            # A flat channel still needs a non-degenerate range in the header.
            lo, hi = lo - 1.0, lo + 1.0
        # A little headroom so rounding cannot push a sample past the limit.
        span = (hi - lo) * 0.01
        lo, hi = lo - span, hi + span
        phys_min[i], phys_max[i] = lo, hi

        scaled = (micro[i] - lo) / (hi - lo) * (DIGITAL_MAX - DIGITAL_MIN) + DIGITAL_MIN
        digital[i] = np.clip(np.round(scaled), DIGITAL_MIN, DIGITAL_MAX).astype(np.int16)

    header = bytearray()
    header += _fixed("0", 8)
    header += _fixed(patient, 80)
    header += _fixed(recording_id, 80)
    header += _fixed("01.01.85", 8)
    header += _fixed("00.00.00", 8)
    header += _fixed(str(256 + 256 * n_ch), 8)
    header += _fixed("", 44)
    header += _fixed(str(n_records), 8)
    header += _num(record_seconds, 8)
    header += _fixed(str(n_ch), 4)

    names = [n[:16] for n in rec.ch_names]
    header += b"".join(_fixed(n, 16) for n in names)
    header += b"".join(_fixed("", 80) for _ in range(n_ch))          # transducer
    header += b"".join(_fixed("uV", 8) for _ in range(n_ch))         # physical dimension
    header += b"".join(_num(v, 8) for v in phys_min)
    header += b"".join(_num(v, 8) for v in phys_max)
    header += b"".join(_fixed(str(DIGITAL_MIN), 8) for _ in range(n_ch))
    header += b"".join(_fixed(str(DIGITAL_MAX), 8) for _ in range(n_ch))
    header += b"".join(_fixed("", 80) for _ in range(n_ch))          # prefiltering
    header += b"".join(_fixed(str(samples_per_record), 8) for _ in range(n_ch))
    header += b"".join(_fixed("", 32) for _ in range(n_ch))          # reserved

    # Records are stored channel by channel within each record.
    blocks = digital.reshape(n_ch, n_records, samples_per_record)
    body = np.transpose(blocks, (1, 0, 2)).reshape(-1).astype("<i2").tobytes()

    with open(path, "wb") as fh:
        fh.write(bytes(header))
        fh.write(body)

    return len(header) + len(body)
