"""Format dispatch.

Sniffs by magic bytes first and falls back to the extension, so a file the
browser hands over without a usable name still loads.
"""

from __future__ import annotations

import os

from ..recording import Recording
from .edf import EDFError, read_edf, sniff_is_edf
from .eeglab import read_set, sniff_is_matlab

__all__ = ["load", "read_edf", "read_set", "EDFError", "UnsupportedFormat"]


class UnsupportedFormat(ValueError):
    pass


SUPPORTED = {
    ".edf": "EDF / EDF+",
    ".bdf": "BioSemi BDF",
    ".set": "EEGLAB",
}


def _head(source, n: int = 512) -> bytes:
    if isinstance(source, (bytes, bytearray, memoryview)):
        return bytes(source[:n])
    with open(source, "rb") as fh:
        return fh.read(n)


def load(source, *, filename: str | None = None) -> Recording:
    """Read any supported EEG file into a :class:`Recording`."""
    head = _head(source)

    if sniff_is_edf(head):
        return read_edf(source)
    if sniff_is_matlab(head):
        return read_set(source)

    name = filename or (source if isinstance(source, (str, os.PathLike)) else "")
    ext = os.path.splitext(str(name))[1].lower()

    if ext in (".edf", ".bdf"):
        return read_edf(source)
    if ext == ".set":
        return read_set(source)

    known = ", ".join(sorted(SUPPORTED))
    raise UnsupportedFormat(
        f"Could not identify this file as EEG data"
        + (f" ({ext})" if ext else "")
        + f". Supported in the browser: {known}. "
        "Other formats (.fif, BrainVision, BIDS trees) are supported by the "
        "local command-line tool, which can use MNE."
    )
