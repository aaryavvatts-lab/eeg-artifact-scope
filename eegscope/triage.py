"""Channel triage: decide what is actually analysable before anything is scored.

This runs before every detector, because getting it wrong silently corrupts
every downstream number. It drops dead channels and non-EEG traces, normalizes
bipolar names so montage lookup works, and -- deliberately -- keeps channels
that merely *look* like vendor placeholders, since dataset 03's "Add_lead*"
channels turned out to carry real signal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from .recording import Recording

# Standard 10-20 / 10-10 labels we recognise after normalization. Used to tell a
# real electrode from a vendor placeholder.
_TEN_TWENTY = {
    "fp1", "fpz", "fp2", "af7", "af3", "afz", "af4", "af8",
    "f9", "f7", "f5", "f3", "f1", "fz", "f2", "f4", "f6", "f8", "f10",
    "ft9", "ft7", "fc5", "fc3", "fc1", "fcz", "fc2", "fc4", "fc6", "ft8", "ft10",
    "t9", "t7", "t3", "c5", "c3", "c1", "cz", "c2", "c4", "c6", "t4", "t8", "t10",
    "tp9", "tp7", "cp5", "cp3", "cp1", "cpz", "cp2", "cp4", "cp6", "tp8", "tp10",
    "p9", "p7", "t5", "p5", "p3", "p1", "pz", "p2", "p4", "p6", "t6", "p8", "p10",
    "po7", "po3", "poz", "po4", "po8", "o1", "oz", "o2", "iz",
    "a1", "a2", "m1", "m2",
}

# Vendor placeholders for unwired inputs.
_PLACEHOLDER = re.compile(r"^(add[_ ]?lead|unused|spare|empty|n/?a|ch)\d*$", re.I)

# Frontal sites where a blink is largest. Ordered by usefulness as a virtual EOG.
FRONTAL_PRIORITY = ["fp1", "fp2", "fpz", "af7", "af8", "af3", "af4", "f7", "f8", "f3", "f4"]


@dataclass
class TriageReport:
    """What triage decided, and why. Surfaced in the UI so nothing is silent."""

    kept: list[str] = field(default_factory=list)
    flat: list[str] = field(default_factory=list)
    # Kept, not excluded: channels whose *name* looks like a vendor placeholder
    # but which carry signal. Recorded so the UI can say so.
    placeholder: list[str] = field(default_factory=list)
    non_eeg: list[str] = field(default_factory=list)
    duplicate: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def n_kept(self) -> int:
        return len(self.kept)

    def as_dict(self) -> dict:
        return {
            "kept": self.kept,
            "excluded": {
                "flat": self.flat,
                "non_eeg": self.non_eeg,
                "duplicate": self.duplicate,
            },
            "kept_but_suspicious": {"placeholder_named": self.placeholder},
            "warnings": self.warnings,
        }


def normalize_name(name: str) -> str:
    """``'Fp1-A1'`` -> ``'fp1'``. Strips bipolar references and separators.

    Dataset 03 labels every channel against its mastoid (``Fp1-A1``), which
    otherwise matches no montage.
    """
    s = name.strip().lower()
    s = re.sub(r"\s+", "", s)
    # Bipolar pair: keep the active site when the reference is a known one.
    if "-" in s:
        head, _, tail = s.partition("-")
        if head in _TEN_TWENTY or tail in {"a1", "a2", "m1", "m2", "ref", "avg", "cz"}:
            s = head
    return s.replace("_", "").replace(".", "")


def is_flat(x: np.ndarray, *, rtol: float = 1e-12) -> bool:
    """True when a channel carries no signal at all.

    Uses standard deviation against the recording's own scale rather than an
    absolute threshold, so it works for volts and for unscaled integers alike.
    """
    if x.size == 0:
        return True
    sd = float(np.std(x))
    return sd <= rtol or not np.isfinite(sd)


def triage(rec: Recording, *, drop_flat: bool = True) -> tuple[Recording, TriageReport]:
    """Return the analysable subset of ``rec`` plus an explanation.

    Keeps only scalp EEG channels that carry signal. EOG/ECG channels are
    excluded from the EEG subset but *not* discarded — callers reach them
    through the original recording, since they are ground truth for validation.
    """
    report = TriageReport()
    keep: list[int] = []
    seen: dict[str, int] = {}

    # Scale reference for flatness: the typical spread across the recording.
    eeg_idx = [i for i, t in enumerate(rec.ch_types) if t == "eeg"]
    if eeg_idx:
        spreads = np.std(rec.data[eeg_idx], axis=1)
        finite = spreads[np.isfinite(spreads) & (spreads > 0)]
        scale = float(np.median(finite)) if finite.size else 0.0
    else:
        scale = 0.0
    flat_tol = max(scale * 1e-6, 1e-15)

    for i, (name, ctype) in enumerate(zip(rec.ch_names, rec.ch_types)):
        norm = normalize_name(name)

        if ctype != "eeg":
            report.non_eeg.append(name)
            continue

        if norm in seen:
            report.duplicate.append(name)
            continue

        if drop_flat and is_flat(rec.data[i], rtol=flat_tol):
            report.flat.append(name)
            continue

        # A vendor placeholder name is a hint, not proof. Dataset 03's
        # "Add_lead1..16" carry 9-17 uV of real signal and are statistically
        # indistinguishable from its named channels, so dropping them on the
        # name alone silently discarded half the montage. Only genuinely dead
        # channels are dropped (above); a live placeholder is kept and flagged.
        if _PLACEHOLDER.match(norm):
            report.placeholder.append(name)

        seen[norm] = i
        keep.append(i)
        report.kept.append(name)

    if not keep:
        report.warnings.append("No analysable EEG channels remain after triage.")
        return rec.subset([], "+triaged"), report

    # Plausibility check on the reader's unit assumption.
    median_amp = float(np.median(np.abs(rec.data[keep])))
    if median_amp > 1e-2:
        report.warnings.append(
            f"Median amplitude {median_amp * 1e3:.1f} mV is far above scalp EEG; "
            "the file's unit field may be wrong."
        )
    elif 0 < median_amp < 1e-9:
        report.warnings.append(
            f"Median amplitude {median_amp * 1e9:.2f} nV is far below scalp EEG; "
            "the file's unit field may be wrong."
        )

    if report.placeholder:
        report.warnings.append(
            f"{len(report.placeholder)} channel(s) are named like unused vendor "
            f"inputs ({', '.join(report.placeholder[:3])}"
            + ("..." if len(report.placeholder) > 3 else "")
            + ") but carry signal, so they were kept. Check they are real electrodes."
        )

    n_named = sum(1 for n in report.kept if normalize_name(n) in _TEN_TWENTY)
    if report.kept and n_named == 0:
        report.warnings.append(
            "No channel names match a standard 10-20 montage; "
            "spatial checks will be skipped."
        )

    return rec.subset(keep, "+triaged"), report


def virtual_eog_index(rec: Recording) -> list[int]:
    """Channels to build a virtual EOG from when no real EOG exists.

    This is the common real-world case: consumer headsets have no EOG
    electrodes, so blinks must be found from frontal EEG. Returns the most
    frontal channels available, or all of them for a single-channel device
    (where the one electrode sits at Fp1 anyway).
    """
    norm = [normalize_name(n) for n in rec.ch_names]
    ranked = [i for site in FRONTAL_PRIORITY for i, n in enumerate(norm) if n == site]

    # De-duplicate, preserving priority order.
    out: list[int] = []
    for i in ranked:
        if i not in out:
            out.append(i)

    if out:
        return out
    # No recognisable frontal site: a 1-2 channel consumer device, or an
    # unnamed montage. Use everything -- a blink dominates whatever it touches.
    return list(range(rec.n_channels))
