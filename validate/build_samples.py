"""Cut example recordings out of the public datasets for the website.

These let a visitor try the tool without owning an EEG file. Every one is a
real excerpt, chosen so the set covers clean and ruined recordings, one to
thirty two electrodes, and each kind of artifact the tool looks for.

    python -m validate.build_samples

Writes web/public/samples/*.edf plus a manifest the page reads.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from eegscope.pipeline import analyse
from eegscope.readers.edf import read_edf
from eegscope.recording import Recording
from eegscope.writers.edf import write_edf

from .common import D01_SOURCE, D02, D03, ROOT, segments

OUT = ROOT / "web" / "public" / "samples"

# Attribution shown on the page for each source dataset.
SOURCES = {
    "ds01": {
        "name": "EEG dataset of consumer- and research-grade systems",
        "authors": "Ahn, M. and Lee, Y. (2026)",
        "url": "https://doi.org/10.6084/m9.figshare.30162868",
        "licence": "CC BY 4.0",
    },
    "ds02": {
        "name": "OpenNeuro ds002718, from Wakeman and Henson (2015)",
        "authors": "Wakeman, D. G. and Henson, R. N.",
        "url": "https://openneuro.org/datasets/ds002718",
        "licence": "CC0",
    },
    "ds03": {
        "name": "iNCog-EEG",
        "authors": "Published on Figshare",
        "url": "https://figshare.com/articles/dataset/iNCog-EEG_ideal_vs_Noisy_Cognitive_EEG_for_Workload_Assessment_Dataset/30003127",
        "licence": "CC BY 4.0",
    },
}


@dataclass
class Sample:
    slug: str
    title: str
    group: str
    device: str
    source: str
    about: str
    look_for: str
    window: tuple[float, float]
    path: Path | None = None
    picks: list[str] | None = None
    rename: dict[str, str] = field(default_factory=dict)


def ds01(sub: str, task: str, dev: str) -> Path:
    return D01_SOURCE / sub / f"{sub}_task-{task}_acq-{dev}_eeg.edf"


# Chosen from a sweep over the whole dataset so the set is genuinely varied
# rather than ten versions of the same recording.
SAMPLES: list[Sample] = [
    Sample(
        slug="clean-single-electrode",
        title="Resting, one electrode",
        group="Clean recordings",
        device="MindWave 2, 1 electrode, 512 Hz",
        source="ds01",
        about="A person sitting still with a single forehead electrode, before any task started.",
        look_for="A high score. This is roughly the best a one electrode headset can do.",
        window=(6.0, 50.0),
        path=ds01("sub-03", "EB", "MW2"),
    ),
    Sample(
        slug="clean-headband",
        title="Resting, four electrode headband",
        group="Clean recordings",
        device="Muse 2, 4 electrodes, 256 Hz",
        source="ds01",
        about="The same idea on a Muse 2. Two electrodes behind the ears, two on the forehead.",
        look_for="A high score, and a note that the electrode agreement check was skipped. Four electrodes are too far apart to cross-check.",
        window=(6.0, 50.0),
        path=ds01("sub-03", "EB", "Muse2"),
    ),
    Sample(
        slug="clean-research-cap",
        title="Resting, research cap",
        group="Clean recordings",
        device="DSI-24, 20 electrodes, 300 Hz",
        source="ds01",
        about="A research grade dry electrode cap at rest. Dry electrodes need no gel, which makes them fast to fit and noisier than wet ones.",
        look_for="A good score, but usually not as clean as you might expect from research hardware.",
        window=(6.0, 44.0),
        path=ds01("sub-03", "EB", "DSI"),
    ),
    Sample(
        slug="blinking-headband",
        title="Blinking on cue, headband",
        group="One artifact at a time",
        device="Muse 2, 4 electrodes, 256 Hz",
        source="ds01",
        about="The same person as the clean headband example, one minute later, blinking every three seconds on a beep.",
        look_for="A blink every three seconds in the timeline, because that is when the beep went. The forehead electrodes sit right above the eyes.",
        window=(62.0, 126.0),
        path=ds01("sub-03", "EB", "Muse2"),
    ),
    Sample(
        slug="blinking-single-electrode",
        title="Blinking on cue, one electrode",
        group="One artifact at a time",
        device="BrainLink Pro, 1 electrode, 512 Hz",
        source="ds01",
        about="Cued blinking recorded through a single forehead electrode, which is where a blink is largest.",
        look_for="Blinks found from one channel with nothing to cross-check against. This is the hardest case for any artifact tool.",
        window=(62.0, 126.0),
        path=ds01("sub-03", "EB", "BLP"),
    ),
    Sample(
        slug="jaw-clench-headband",
        title="Clenching the jaw, headband",
        group="One artifact at a time",
        device="Muse 2, 4 electrodes, 256 Hz",
        source="ds01",
        about="Cued jaw clenching. Muscle activity from the jaw is fast and spread across frequencies.",
        look_for="A large muscle penalty and a big drop in usable time. Compare it against the clean headband example from the same person.",
        window=(62.0, 126.0),
        path=ds01("sub-03", "BT", "Muse2"),
    ),
    Sample(
        slug="jaw-clench-research-cap",
        title="Clenching the jaw, research cap",
        group="One artifact at a time",
        device="DSI-24, 20 electrodes, 300 Hz",
        source="ds01",
        about="The same jaw clenching task on twenty electrodes, so you can see which parts of the head it reaches.",
        look_for="Muscle dominating the breakdown, and the per electrode detail showing it strongest near the temples.",
        window=(62.0, 100.0),
        path=ds01("sub-03", "BT", "DSI"),
    ),
    Sample(
        slug="head-movement-bad-electrodes",
        title="Head movement with failing electrodes",
        group="Harder cases",
        device="DSI-24, 20 electrodes, 300 Hz",
        source="ds01",
        about="Cued head turns with the eyes closed. Movement pulls on the cap and some contacts start to fail.",
        look_for="Several electrodes flagged as bad, and electrode pops in the timeline. This is the recording most worth acting on.",
        window=(62.0, 100.0),
        path=ds01("sub-03", "MVC", "DSI"),
    ),
    Sample(
        slug="filtered-clinical",
        title="A clinical recording that was filtered",
        group="Harder cases",
        device="Clinical system, 32 electrodes, 200 Hz",
        source="ds03",
        about="A 32 channel clinical recording. It samples at 200 Hz, which looks fast enough to see muscle activity, but the signal was filtered away above about 38 Hz before it was saved.",
        look_for="Muscle reported as not assessed rather than clean. A check that could not run is not a pass, and this is the case that taught me to say so.",
        window=(2.0, 50.0),
        path=D03 / "sub01" / "sub01_hw.edf",
    ),
    Sample(
        slug="eye-and-heart-electrodes",
        title="With real eye and heart electrodes",
        group="Harder cases",
        device="Research cap, 20 EEG plus 4 reference, 250 Hz",
        source="ds02",
        about="A face perception study recorded with electrodes placed specifically to pick up eye movement and heartbeat, alongside the EEG.",
        look_for="Blinks found from the real eye electrodes instead of guessed from the forehead, and a heartbeat rate reported with high confidence.",
        window=(60.0, 100.0),
        path=None,  # built separately from the EEGLAB file
        picks=[f"EEG{i:03d}" for i in range(1, 21)] + ["EEG061", "EEG062", "EEG063", "EEG064"],
        rename={"EEG061": "HEOG", "EEG062": "VEOG", "EEG063": "ECG1", "EEG064": "ECG2"},
    ),
]


def _load_ds02(s: Sample) -> Recording | None:
    """Pull a small excerpt out of the 234 MB EEGLAB file."""
    from eegscope.readers.eeglab import read_set

    matches = sorted((D02 / "sub-002" / "eeg").glob("*_eeg.set"))
    if not matches:
        return None
    rec = read_set(matches[0])

    idx = [rec.ch_names.index(n) for n in (s.picks or []) if n in rec.ch_names]
    if not idx:
        return None
    sub = rec.subset(idx)
    sub.ch_names = [s.rename.get(n, n) for n in sub.ch_names]

    # Re-derive types from the new names so the eye and heart channels are
    # recognised by any reader, not only one that has the BIDS sidecar.
    from eegscope.recording import guess_channel_type

    sub.ch_types = [guess_channel_type(n) for n in sub.ch_names]
    return sub


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    for s in SAMPLES:
        if s.path is not None:
            if not s.path.exists():
                print(f"  skip {s.slug}: missing {s.path.name}")
                continue
            rec = read_edf(s.path)
            origin = s.path.name
        else:
            rec = _load_ds02(s)
            origin = "sub-002_task-FaceRecognition_eeg.set"
            if rec is None:
                print(f"  skip {s.slug}: could not build from dataset 02")
                continue

        lo, hi = s.window
        hi = min(hi, rec.duration)
        if hi - lo < 10.0:
            print(f"  skip {s.slug}: window too short")
            continue
        clip = rec.crop(lo, hi)

        out_path = OUT / f"{s.slug}.edf"
        size = write_edf(clip, out_path, recording_id=f"Startdate X X X {s.slug}")

        # Run the real pipeline so the manifest can state what it produces.
        # If this disagrees with the site, the site is wrong.
        result = analyse(out_path)
        q = result.quality
        top = [c for c in q.components if not c.skipped and c.penalty > 0.2]
        dominant = max(top, key=lambda c: c.penalty).label if top else None

        manifest.append(
            {
                "slug": s.slug,
                "title": s.title,
                "group": s.group,
                "device": s.device,
                "about": s.about,
                "look_for": s.look_for,
                "file": f"/samples/{s.slug}.edf",
                "bytes": size,
                "seconds": round(clip.duration, 1),
                "channels": clip.n_channels,
                "channels_analysed": result.triaged.n_channels,
                "sfreq": clip.sfreq,
                "source": {**SOURCES[s.source], "file": origin, "window_s": [lo, round(hi, 1)]},
                "expected": {
                    "score": round(q.score, 1),
                    "grade": q.grade,
                    "dominant": dominant,
                    "usable_fraction": round(q.usable_fraction, 3),
                    "bad_channels": len(q.bad_channels),
                    "skipped": len(q.skipped),
                },
            }
        )
        print(
            f"  {s.slug:32s} {size / 1024:6.0f} KB  {clip.n_channels:2d}ch  "
            f"{clip.duration:4.0f}s  score {q.score:5.1f} ({q.grade})  {dominant or 'clean'}"
        )

    payload = {
        "note": (
            "Real excerpts from public datasets. Every expected score below was "
            "produced by running the shipped pipeline on the exact file offered "
            "for download, so the page and the tool cannot drift apart."
        ),
        "samples": manifest,
    }
    (OUT / "manifest.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    return payload


def main() -> int:
    print("Building example recordings")
    data = build()
    total = sum(s["bytes"] for s in data["samples"]) / 1024 / 1024
    print(f"\n{len(data['samples'])} samples, {total:.1f} MB total")
    print(f"Manifest: {(OUT / 'manifest.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
