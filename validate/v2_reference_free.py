"""V2 - Blink detection without EOG electrodes (dataset 02).

The real-world case: no consumer headset has EOG electrodes, so blinks must be
found from frontal EEG alone. Dataset 02 has dedicated VEOG and HEOG channels
*and* 70 EEG channels, so the reference-free path can be scored against the
reference-channel path on the same recording, sample for sample.

MNE is used here as the independent reference implementation rather than our
own EOG-channel path, so this is a genuine cross-check rather than the code
agreeing with itself.
"""

from __future__ import annotations

import numpy as np

from eegscope.detect.blink import detect_blinks
from eegscope.readers.eeglab import read_set
from eegscope.triage import triage

from .common import D02, summarise

# Two detections describe the same blink if they land within this of each other.
TOLERANCE_S = 0.5
# Full recordings are ~50 min at 250 Hz; a slice keeps the suite quick while
# still covering thousands of blinks.
ANALYSE_SECONDS = 300.0


def _f1(matched: int, n_ref: int, n_test: int) -> tuple[float, float, float]:
    precision = matched / n_test if n_test else 0.0
    recall = matched / n_ref if n_ref else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def _match(a: list[float], b: list[float], tol: float = TOLERANCE_S) -> int:
    """Greedy one-to-one matching between two event lists."""
    used: set[int] = set()
    n = 0
    for t in a:
        for j, u in enumerate(b):
            if j in used:
                continue
            if abs(t - u) <= tol:
                used.add(j)
                n += 1
                break
    return n


def run(max_subjects: int | None = None, verbose: bool = True) -> dict:
    out: dict = {
        "description": (
            "Blink detection from frontal EEG only, scored against dedicated "
            "VEOG/HEOG electrodes and against MNE's find_eog_events"
        ),
        "tolerance_s": TOLERANCE_S,
        "subjects": [],
    }

    try:
        import mne

        mne.set_log_level("ERROR")
    except ImportError:
        out["skipped"] = "MNE not installed; V2 needs it as the reference"
        return out

    subs = sorted(p for p in D02.glob("sub-*") if p.is_dir())
    if max_subjects:
        subs = subs[:max_subjects]
    if not subs:
        out["skipped"] = f"dataset 02 not found at {D02}"
        return out

    f1_vs_ours, f1_vs_mne, ratios = [], [], []

    for sub in subs:
        matches = list((sub / "eeg").glob("*_eeg.set"))
        if not matches:
            continue
        path = matches[0]

        rec = read_set(path)
        if not rec.picks("eog"):
            continue

        rec = rec.crop(0.0, min(ANALYSE_SECONDS, rec.duration))

        # (a) our detector using the real EOG electrodes
        ref = detect_blinks(rec)
        ref_times = [e.onset for e in ref.events]

        # (b) our detector using frontal EEG only -- the consumer-hardware case
        eeg_only, _ = triage(rec)
        test = detect_blinks(eeg_only)
        test_times = [e.onset for e in test.events]

        # (c) MNE's own EOG event finder, as an independent reference
        mne_times: list[float] = []
        try:
            import mne

            info = mne.create_info(
                rec.ch_names, rec.sfreq, ch_types=[
                    {"eeg": "eeg", "eog": "eog", "ecg": "ecg", "emg": "emg"}.get(t, "misc")
                    for t in rec.ch_types
                ],
            )
            raw = mne.io.RawArray(rec.data, info, verbose="ERROR")
            events = mne.preprocessing.find_eog_events(raw, verbose="ERROR")
            mne_times = list(events[:, 0] / rec.sfreq)
        except Exception as exc:  # reported, not swallowed
            out.setdefault("mne_errors", []).append(f"{sub.name}: {type(exc).__name__}")

        m_ours = _match(ref_times, test_times)
        p1, r1, f1a = _f1(m_ours, len(ref_times), len(test_times))

        f1b = None
        if mne_times:
            m_mne = _match(mne_times, test_times)
            _, _, f1b = _f1(m_mne, len(mne_times), len(test_times))
            f1_vs_mne.append(f1b)

        f1_vs_ours.append(f1a)
        if ref_times:
            ratios.append(len(test_times) / len(ref_times))

        out["subjects"].append(
            {
                "subject": sub.name,
                "n_eog_reference": len(ref_times),
                "n_eeg_only": len(test_times),
                "n_mne_reference": len(mne_times),
                "precision": round(p1, 4),
                "recall": round(r1, 4),
                "f1_vs_eog_channels": round(f1a, 4),
                "f1_vs_mne": None if f1b is None else round(f1b, 4),
            }
        )

        if verbose:
            print(
                f"  {sub.name:9s} EOG-ref {len(ref_times):4d}  EEG-only {len(test_times):4d}  "
                f"MNE {len(mne_times):4d}  F1 vs EOG {f1a:.3f}"
                + (f"  F1 vs MNE {f1b:.3f}" if f1b is not None else "")
            )

    out["summary"] = {
        "f1_vs_eog_channels": summarise(f1_vs_ours),
        "f1_vs_mne": summarise(f1_vs_mne),
        "detections_ratio_eeg_only_over_eog": summarise(ratios),
    }
    return out
