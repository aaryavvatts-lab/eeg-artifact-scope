"""The single interchange type every reader produces and every detector consumes.

Deliberately depends on numpy only. Everything in ``core`` must stay importable
inside Pyodide, where MNE is not available.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

# Channel names that are not scalp EEG. Matched case-insensitively against the
# normalized name. Kept here rather than in triage so readers can pre-tag.
_NON_EEG_HINTS = {
    "eog": ("eog", "veog", "heog", "veo", "heo"),
    "ecg": ("ecg", "ekg"),
    "emg": ("emg",),
    "misc": (
        "annotation",
        "annotations",
        "status",
        "trigger",
        "marker",
        "timestamp",
        "timest",
        "aux",
        "x1",
        "x2",
        "x3",
        "counter",
        "battery",
    ),
}


@dataclass
class Recording:
    """A continuous multichannel recording.

    Attributes
    ----------
    data
        ``(n_channels, n_samples)`` float64, in **volts**. Readers are
        responsible for scaling; detectors assume volts throughout.
    sfreq
        Sampling frequency in Hz.
    ch_names
        Channel labels, same order as ``data``'s first axis.
    ch_types
        Per-channel type: ``eeg``, ``eog``, ``ecg``, ``emg`` or ``misc``.
    source_format
        Reader that produced this, e.g. ``"edf"``. Informational.
    meta
        Free-form extras (device hints, original header fields).
    """

    data: np.ndarray
    sfreq: float
    ch_names: list[str]
    ch_types: list[str]
    source_format: str = "unknown"
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.data = np.asarray(self.data, dtype=np.float64)
        if self.data.ndim != 2:
            raise ValueError(f"data must be 2-D (n_channels, n_samples), got {self.data.shape}")
        n_ch = self.data.shape[0]
        if len(self.ch_names) != n_ch:
            raise ValueError(f"{len(self.ch_names)} names for {n_ch} channels")
        if len(self.ch_types) != n_ch:
            raise ValueError(f"{len(self.ch_types)} types for {n_ch} channels")
        if self.sfreq <= 0:
            raise ValueError(f"sfreq must be positive, got {self.sfreq}")

    # -- shape -----------------------------------------------------------

    @property
    def n_channels(self) -> int:
        return self.data.shape[0]

    @property
    def n_samples(self) -> int:
        return self.data.shape[1]

    @property
    def duration(self) -> float:
        """Length in seconds."""
        return self.n_samples / self.sfreq

    def times(self) -> np.ndarray:
        return np.arange(self.n_samples) / self.sfreq

    # -- selection -------------------------------------------------------

    def picks(self, *types: str) -> list[int]:
        """Indices of channels whose type is any of ``types``."""
        wanted = set(types)
        return [i for i, t in enumerate(self.ch_types) if t in wanted]

    def pick_names(self, *types: str) -> list[str]:
        return [self.ch_names[i] for i in self.picks(*types)]

    def subset(self, idx: list[int], source_suffix: str = "") -> "Recording":
        """A new Recording containing only ``idx``, in that order."""
        return replace(
            self,
            data=self.data[idx],
            ch_names=[self.ch_names[i] for i in idx],
            ch_types=[self.ch_types[i] for i in idx],
            source_format=self.source_format + source_suffix,
        )

    def crop(self, tmin: float = 0.0, tmax: float | None = None) -> "Recording":
        """Time-slice in seconds. ``tmax=None`` means to the end."""
        a = max(0, int(round(tmin * self.sfreq)))
        b = self.n_samples if tmax is None else min(self.n_samples, int(round(tmax * self.sfreq)))
        if b <= a:
            raise ValueError(f"empty crop: tmin={tmin} tmax={tmax}")
        return replace(self, data=self.data[:, a:b])

    def __repr__(self) -> str:  # pragma: no cover - display only
        kinds = ", ".join(f"{t}={self.ch_types.count(t)}" for t in sorted(set(self.ch_types)))
        return (
            f"<Recording {self.n_channels}ch x {self.n_samples} @ {self.sfreq:g}Hz "
            f"({self.duration:.1f}s) [{kinds}] from {self.source_format}>"
        )


def guess_channel_type(name: str) -> str:
    """Best-effort channel type from its label alone.

    Readers that carry real type information should use it and skip this.
    """
    low = name.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    for kind, hints in _NON_EEG_HINTS.items():
        for h in hints:
            # Substring for the descriptive hints, exact for the short aux codes
            # so a channel legitimately named "X" isn't caught by "x1".
            if len(h) <= 2:
                if low == h:
                    return kind
            elif h in low:
                return kind
    return "eeg"
