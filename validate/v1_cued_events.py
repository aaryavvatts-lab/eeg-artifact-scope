"""V1 - Detection accuracy against cued ground truth (dataset 01).

30 subjects each performed 20 cued eye blinks and 20 cued jaw clenches, three
seconds apart, while wearing five headsets simultaneously. The cue timestamps
are in the EDF annotations, so this measures the detectors against events we
know actually happened.

Two honest limits, both reported alongside the numbers:

* The beep is an *instruction*, not a measured onset. Response latency varies,
  so a detection counts if it lands within the response window rather than at
  an exact time.
* Precision against cues is not meaningful, because subjects also blink
  spontaneously between cues and those detections are correct. Recall and
  detections-per-cue are what the data can actually support.
"""

from __future__ import annotations

import numpy as np

from eegscope.detect.blink import detect_blinks
from eegscope.detect.muscle import detect_muscle
from eegscope.readers.edf import read_edf
from eegscope.triage import triage

from .common import DEVICES, D01_SOURCE, match_events, segments, summarise


def _rate(events, lo: float, hi: float) -> float:
    """Events per minute inside a window."""
    span = max(hi - lo, 1e-9)
    n = sum(1 for e in events if lo <= e.onset <= hi)
    return n / (span / 60.0)


def run(max_subjects: int | None = None, verbose: bool = True) -> dict:
    out: dict = {"description": "Detector accuracy vs cued beep timestamps", "devices": {}}

    subjects = sorted(p.name for p in D01_SOURCE.glob("sub-*") if p.is_dir())
    if max_subjects:
        subjects = subjects[:max_subjects]

    for dev, meta in DEVICES.items():
        recall_blink, per_cue_blink = [], []
        task_rate_b, rest_rate_b = [], []
        muscle_task, muscle_rest, muscle_skipped = [], [], 0
        blink_amp_frontal = []
        n_files = 0

        for sub in subjects:
            path = D01_SOURCE / sub / f"{sub}_task-EB_acq-{dev}_eeg.edf"
            if path.exists():
                rec = read_edf(path)
                seg = segments(rec)
                if seg is not None:
                    tri, _ = triage(rec)
                    if tri.n_channels:
                        n_files += 1
                        res = detect_blinks(tri)
                        times = [e.onset for e in res.events]
                        matched, _, _ = match_events(times, seg.beeps)
                        recall_blink.append(matched / len(seg.beeps))
                        in_task = sum(
                            1 for t in times if seg.task[0] <= t <= seg.task[1]
                        )
                        per_cue_blink.append(in_task / len(seg.beeps))
                        task_rate_b.append(_rate(res.events, *seg.task))
                        rest_rate_b.append(
                            (
                                _rate(res.events, *seg.rest_pre)
                                + _rate(res.events, *seg.rest_post)
                            )
                            / 2
                        )
                        if res.per_channel:
                            blink_amp_frontal.append(max(res.per_channel.values()))

            # Jaw clench: contaminated fraction during the cued minute vs rest.
            path = D01_SOURCE / sub / f"{sub}_task-BT_acq-{dev}_eeg.edf"
            if path.exists():
                rec = read_edf(path)
                seg = segments(rec)
                if seg is not None:
                    tri, _ = triage(rec)
                    if tri.n_channels:
                        m = detect_muscle(tri)
                        if not m.ok:
                            muscle_skipped += 1
                        else:
                            t_lo, t_hi = seg.task
                            covered = sum(
                                max(0.0, min(e.offset, t_hi) - max(e.onset, t_lo))
                                for e in m.events
                            )
                            muscle_task.append(covered / (t_hi - t_lo))
                            rest_span = (seg.rest_pre[1] - seg.rest_pre[0]) + (
                                seg.rest_post[1] - seg.rest_post[0]
                            )
                            rest_cov = m.contaminated_seconds() - covered
                            muscle_rest.append(
                                rest_cov / rest_span if rest_span > 0 else 0.0
                            )

        blink_recall = summarise(recall_blink)
        entry = {
            **meta,
            "n_files": n_files,
            "blink": {
                "recall_of_cued": blink_recall,
                "detections_per_cue": summarise(per_cue_blink),
                "rate_per_min_task": summarise(task_rate_b),
                "rate_per_min_rest": summarise(rest_rate_b),
                "median_blink_amplitude_uv": summarise(blink_amp_frontal),
            },
            "jaw": {
                "contaminated_fraction_task": summarise(muscle_task),
                "contaminated_fraction_rest": summarise(muscle_rest),
                "n_skipped": muscle_skipped,
            },
        }

        mt = entry["jaw"]["contaminated_fraction_task"]["mean"]
        mr = entry["jaw"]["contaminated_fraction_rest"]["mean"]
        entry["jaw"]["task_vs_rest_ratio"] = (
            round(mt / mr, 1) if mt is not None and mr else None
        )

        out["devices"][dev] = entry

        if verbose:
            r = blink_recall["mean"]
            pc = entry["blink"]["detections_per_cue"]["mean"]
            print(
                f"  {meta['label']:16s} blink recall "
                f"{'n/a' if r is None else f'{r:.1%}':>6s}  "
                f"per-cue {'n/a' if pc is None else f'{pc:.2f}':>5s}  "
                f"jaw task/rest "
                f"{entry['jaw']['task_vs_rest_ratio'] or 'n/a'}x"
            )

    return out
