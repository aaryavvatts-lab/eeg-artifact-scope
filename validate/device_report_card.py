"""The Device Report Card.

Dataset 01 recorded the same person performing the same cued blink and the same
cued jaw clench on five headsets **simultaneously**. Same subject, same instant,
five price tiers. That is a natural experiment, and it lets the tool answer a
question a plain quality score cannot: how much of the damage is the hardware?

Three measures per device, all from cued events so they mean something:

* **blink amplitude** -- how many microvolts a blink puts into the electrodes.
  A Muse 2 sits AF7/AF8 directly above the eyes; a 1-electrode headset sits at
  Fp1. Both are about the worst possible place to be during a blink.
* **jaw survivability** -- how much of the clench minute stays usable.
* **score cost** -- how far a cued artifact minute drops the quality score
  relative to the same subject's own rest minute.

One caveat is carried into the output rather than left to the reader: 30
subjects, one lab, one session. These numbers describe these recordings, and
generalise only as far as that.
"""

from __future__ import annotations

import numpy as np

from eegscope.detect.blink import detect_blinks
from eegscope.detect.muscle import detect_muscle
from eegscope.pipeline import analyse
from eegscope.readers.edf import read_edf
from eegscope.triage import triage

from .common import DEVICES, D01_SOURCE, segments, summarise

GRADE_CUTS = [(85, "A"), (70, "B"), (55, "C"), (40, "D"), (0, "F")]


def _grade(value: float) -> str:
    for cut, letter in GRADE_CUTS:
        if value >= cut:
            return letter
    return "F"


def run(max_subjects: int | None = None, verbose: bool = True) -> dict:
    out: dict = {
        "description": "Per-device artifact susceptibility, from simultaneous recordings",
        "caveat": (
            "30 subjects, one laboratory, one session. Blink amplitude depends "
            "on electrode placement and reference, both of which differ between "
            "these devices by design -- that is what is being measured, but it "
            "means the numbers describe these recordings rather than the "
            "hardware in the abstract."
        ),
        "devices": {},
    }

    subjects = sorted(p.name for p in D01_SOURCE.glob("sub-*") if p.is_dir())
    if max_subjects:
        subjects = subjects[:max_subjects]

    for dev, meta in DEVICES.items():
        blink_uv, blink_ratio = [], []
        jaw_usable, blink_cost, jaw_cost = [], [], []

        for sub in subjects:
            # --- blink recording -----------------------------------------
            p = D01_SOURCE / sub / f"{sub}_task-EB_acq-{dev}_eeg.edf"
            if p.exists():
                rec = read_edf(p)
                seg = segments(rec)
                if seg is not None:
                    tri, _ = triage(rec)
                    if tri.n_channels:
                        res = detect_blinks(tri)
                        if res.per_channel:
                            worst = max(res.per_channel.values())
                            blink_uv.append(worst)
                            # Blink size relative to the ongoing EEG it buries.
                            baseline = float(
                                np.median(np.std(tri.crop(*seg.rest_pre).data, axis=1))
                            ) * 1e6
                            if baseline > 0:
                                blink_ratio.append(worst / baseline)
                        r = analyse(rec.crop(*seg.rest_pre)).quality.score
                        t = analyse(rec.crop(*seg.task)).quality.score
                        blink_cost.append(r - t)

            # --- jaw-clench recording ------------------------------------
            p = D01_SOURCE / sub / f"{sub}_task-BT_acq-{dev}_eeg.edf"
            if p.exists():
                rec = read_edf(p)
                seg = segments(rec)
                if seg is not None:
                    tri, _ = triage(rec)
                    if tri.n_channels:
                        m = detect_muscle(tri)
                        if m.ok:
                            lo, hi = seg.task
                            covered = sum(
                                max(0.0, min(e.offset, hi) - max(e.onset, lo))
                                for e in m.events
                            )
                            jaw_usable.append(1.0 - covered / (hi - lo))
                        r = analyse(rec.crop(*seg.rest_pre)).quality.score
                        t = analyse(rec.crop(*seg.task)).quality.score
                        jaw_cost.append(r - t)

        amp = summarise(blink_uv)
        usable = summarise(jaw_usable)
        entry = {
            **meta,
            "blink_amplitude_uv": amp,
            "blink_to_background_ratio": summarise(blink_ratio),
            "jaw_usable_fraction": usable,
            "blink_score_cost": summarise(blink_cost),
            "jaw_score_cost": summarise(jaw_cost),
        }
        # Survivability grade: what fraction of the clench minute stays usable.
        entry["jaw_grade"] = (
            _grade(usable["mean"] * 100) if usable["mean"] is not None else None
        )
        out["devices"][dev] = entry

        if verbose and amp["mean"] is not None:
            ratio = entry["blink_to_background_ratio"]["mean"]
            print(
                f"  {meta['label']:16s} blink {amp['mean']:7.1f} uV "
                f"({ratio:.1f}x background)  jaw usable "
                f"{usable['mean']:.0%} ({entry['jaw_grade']})"
            )

    return out
