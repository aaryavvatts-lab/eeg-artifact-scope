"""V3 - Does the quality score respond to real contamination? (dataset 01)

**This replaces the originally planned clean-vs-noisy test on dataset 03.**
That dataset labels sub01-30 "clean" and sub31-40 "noisy", but measurement
found no difference between the groups on any standard metric -- broadband
amplitude, high-frequency power, drift, line noise and HF ratio all gave AUCs
between 0.48 and 0.64, i.e. chance. See ``v3_dataset03_null.py`` for that
result, which is reported rather than discarded.

What dataset 01 supports is strictly stronger: the *same subject* on the *same
device* in the *same recording*, one minute at rest and one minute performing
cued artifacts. That is a paired within-subject comparison, so it controls for
subject, hardware, electrode placement and session, none of which a
between-subjects comparison controls for.

The test: the cued-artifact minute must score worse than the flanking rest
minutes.
"""

from __future__ import annotations

import numpy as np

from eegscope.pipeline import analyse
from eegscope.readers.edf import read_edf

from .common import DEVICES, D01_SOURCE, TASKS, cohens_d, segments, summarise


def _score(rec, window: tuple[float, float]) -> float | None:
    lo, hi = window
    if hi - lo < 5.0:
        return None
    try:
        return analyse(rec.crop(lo, hi)).quality.score
    except Exception:
        return None


def run(max_subjects: int | None = None, tasks=("EB", "BT"), verbose: bool = True) -> dict:
    out: dict = {
        "description": (
            "Paired within-recording test: rest minute vs cued-artifact minute, "
            "same subject and same device"
        ),
        "replaces": (
            "dataset 03 clean-vs-noisy, which measurement showed does not "
            "separate on any standard metric"
        ),
        "results": {},
    }

    subjects = sorted(p.name for p in D01_SOURCE.glob("sub-*") if p.is_dir())
    if max_subjects:
        subjects = subjects[:max_subjects]

    for dev, meta in DEVICES.items():
        for task in tasks:
            rest_scores, task_scores, drops = [], [], []

            for sub in subjects:
                path = D01_SOURCE / sub / f"{sub}_task-{task}_acq-{dev}_eeg.edf"
                if not path.exists():
                    continue
                rec = read_edf(path)
                seg = segments(rec)
                if seg is None:
                    continue

                rest_parts = [
                    s for s in (_score(rec, seg.rest_pre), _score(rec, seg.rest_post))
                    if s is not None
                ]
                t = _score(rec, seg.task)
                if not rest_parts or t is None:
                    continue

                r = float(np.mean(rest_parts))
                rest_scores.append(r)
                task_scores.append(t)
                drops.append(r - t)

            n = len(drops)
            n_worse = sum(1 for d in drops if d > 0)
            key = f"{dev}_{task}"
            out["results"][key] = {
                "device": meta["label"],
                "device_tier": meta["tier"],
                "task": TASKS[task],
                "n_subjects": n,
                "rest_score": summarise(rest_scores),
                "task_score": summarise(task_scores),
                "score_drop": summarise(drops),
                "n_task_scored_worse": n_worse,
                "fraction_correct_direction": round(n_worse / n, 3) if n else None,
                "cohens_d": (
                    round(cohens_d(rest_scores, task_scores), 3)
                    if cohens_d(rest_scores, task_scores) is not None
                    else None
                ),
            }

            if verbose and n:
                d = out["results"][key]["score_drop"]["mean"]
                print(
                    f"  {meta['label']:16s} {TASKS[task]:26s} "
                    f"drop {d:6.1f}  correct direction {n_worse}/{n}"
                )

    return out
