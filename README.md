# EEG Artifact Scope

Scalp EEG is measured in microvolts. An eye blink is measured in hundreds of
microvolts. So a single blink or jaw clench can be an order of magnitude larger
than the neural signal underneath it — and researchers routinely cannot tell
whether what they recorded is brain activity or their own face.

This is a signal-quality checker for EEG. Drop in a recording, get back which
artifacts are present, where they occur, which channels are bad, and how much
usable data is actually left.

**The recording never leaves your browser.** All analysis runs client-side, which
matters if you work under IRB or GDPR terms that forbid uploading recordings to a
third party.

## The Device Report Card

Most quality tools give you a number with nothing to compare it against. This one
also tells you how much of the damage is your hardware.

That is possible because of an unusual dataset: 30 people performed *cued* eye
blinks and jaw clenches while wearing **five headsets at the same time** — a
1-channel MindWave, a 1-channel BrainLink Pro, a 4-channel Muse 2, a NeuroNicle
FX2, and a research-grade 24-channel DSI-24. Same person, same blink, same
instant, five price tiers. That is a natural experiment, and it turns "your data
is noisy" into "here is how your hardware handles a blink, measured."

## Status

Under active development. See `SCORECARD.md` for validation results as they land.

| Phase | State |
|---|---|
| 0 — Environment, data audit, Pyodide spike | in progress |
| 1 — `eegscope` readers + channel triage | EDF/BDF reader done, verified against MNE |
| 2 — Artifact detectors | not started |
| 3 — Quality scoring | not started |
| 4 — Validation against 4 datasets | not started |
| 5 — Device Report Card | not started |
| 6 — Web app | not started |
| 7 — ML head-to-head | not started |

## Architecture

The project is split by a hard dependency rule:

- **`eegscope/`** — all detection math. Depends only on **numpy, scipy,
  scikit-learn**, which are first-class Pyodide packages. This is what runs in
  the browser, and it is also what runs locally.
- **`labio/`** — MNE-dependent code. Reads research formats (`.fif`, BIDS) and
  acts as the *reference implementation* that `eegscope` is validated against.
  Never imported by `eegscope`.

Vercel caps serverless request bodies at 4.5 MB and function runtime at 60 s;
EEG files here run 50 MB–234 MB. A conventional upload-to-backend design is
therefore impossible on Vercel, which is why the analysis runs in the browser.
`tests/test_parity.py` is what makes that safe: it asserts the dependency-free
readers produce the same samples as MNE on real files.

```
eegscope/          readers, triage, detectors, scoring   (numpy/scipy/sklearn only)
labio/             MNE readers + reference detectors     (offline only)
validate/          V1-V4 against the four datasets       -> benchmark.json, SCORECARD.md
ml/                features, training, rules-vs-ML       (offline only)
web/               Next.js app deployed to Vercel
tests/             parity + unit tests
data/              datasets (gitignored)
```

## Datasets

Not redistributed here. `data/WHERE_TO_PUT_DATA.md` documents the layout.

| # | Dataset | License | Role |
|---|---|---|---|
| 01 | [Consumer vs research-grade EEG systems](https://figshare.com/articles/dataset/EEG_dataset_of_consumer-_and_research-grade_systems/30162868) | CC-BY-4.0 | Cued blink/jaw ground truth; the Device Report Card |
| 02 | [OpenNeuro ds002718](https://openneuro.org/datasets/ds002718) | CC0 | Real VEOG/HEOG/EKG reference channels |
| 03 | [iNCog-EEG](https://figshare.com/articles/dataset/iNCog-EEG_ideal_vs_Noisy_Cognitive_EEG_for_Workload_Assessment_Dataset/30003127) | CC-BY-4.0 | Clean vs noisy score separation |
| 04 | [Semi-simulated EEG/EOG](https://data.mendeley.com/datasets/wb6yvr725d/1) | CC-BY-4.0 | True pre-contamination signal |

### Notes found while auditing the data

Recorded here because they are not in the datasets' own documentation and each
one would silently corrupt results:

- **Dataset 01's `latency` field is in samples, not seconds** — its README says
  seconds. Every recording has exactly 20 cued beeps at 3.0 s intervals, with the
  structure rest (0–61 s) → cued task (61–124 s) → rest (124–184 s).
- **Dataset 01's EDF files leave the physical-dimension field blank**, which
  violates the EDF spec. MNE reads blank as volts and reports ±176 V at the
  scalp, which is physically impossible. `eegscope` reads blank as microvolts and
  records the assumption in `meta["assumed_microvolts"]`.
- **Dataset 03's clean/noisy split is between subjects** (sub01–30 clean,
  sub31–40 noisy), not paired recordings — so that comparison is a group
  difference, not a within-subject test.
- **Dataset 03 ships 16 all-zero `Add_lead*` channels.** A naive flat-channel
  detector flags them and falsely tanks every score. Channel triage runs first.
- **Sample rates differ per device** (DSI 300 Hz, Muse 2 256 Hz, MindWave and
  BrainLink 512 Hz) and Muse channel counts vary between subjects (4 or 6).

## Development

```bash
uv venv --python 3.12
uv pip install -e ".[lab,dev]"
uv run pytest
```

## License

MIT. The datasets keep their own licenses, listed above.
