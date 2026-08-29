"""Parity: eegscope's dependency-free readers vs MNE on the real datasets.

This is the test that lets us trust ``eegscope`` in the browser, where MNE cannot
run. If it passes, the same bytes produce the same samples with and without MNE.

Skips itself when the datasets are absent so the suite still runs on a clean
checkout (``data/`` is gitignored).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from eegscope.readers.edf import read_edf

mne = pytest.importorskip("mne")

DATA = Path(__file__).resolve().parents[1] / "data"
D01 = DATA / "01_blink_jaw_devices" / "30162868" / "sourcedata"
D03 = DATA / "03_incog_clean_vs_noisy" / (
    "iNCog-EEG (ideal vs. Noisy Cognitive EEG for Workload_Assessment) Dataset"
)

# (id, path, whether the file leaves the physical-dimension field blank)
CASES = [
    ("dsi-23ch-300hz", D01 / "sub-01" / "sub-01_task-EB_acq-DSI_eeg.edf", True),
    ("muse2-256hz", D01 / "sub-01" / "sub-01_task-EB_acq-Muse2_eeg.edf", True),
    ("mindwave-1ch-512hz", D01 / "sub-01" / "sub-01_task-EB_acq-MW2_eeg.edf", True),
    ("brainlink-1ch-512hz", D01 / "sub-01" / "sub-01_task-EB_acq-BLP_eeg.edf", True),
    ("incog-32ch-200hz", D03 / "sub01" / "sub01_nw.edf", False),
    ("incog-noisy-subject", D03 / "sub31" / "sub31_hw.edf", False),
]


@pytest.fixture(scope="module", autouse=True)
def _quiet_mne():
    mne.set_log_level("ERROR")


def _load(path: Path):
    ours = read_edf(path)
    raw = mne.io.read_raw_edf(path, preload=True, verbose="ERROR")
    return ours, raw


@pytest.mark.parametrize("name,path,blank_unit", CASES, ids=[c[0] for c in CASES])
def test_matches_mne(name, path, blank_unit):
    if not path.exists():
        pytest.skip(f"dataset not present: {path}")

    ours, raw = _load(path)

    assert ours.sfreq == pytest.approx(raw.info["sfreq"]), "sample rate disagrees"
    assert ours.n_samples == raw.n_times, "sample count disagrees"

    shared = [c for c in ours.ch_names if c in raw.ch_names]
    assert shared, f"no shared channel names: {ours.ch_names[:5]} vs {raw.ch_names[:5]}"

    oi = [ours.ch_names.index(c) for c in shared]
    mi = [raw.ch_names.index(c) for c in shared]
    a = ours.data[oi]
    b = raw.get_data()[mi]

    # MNE reads a blank physical dimension as volts; we read it as microvolts
    # (see eegscope/readers/edf.py). Undo that known, intentional factor.
    if blank_unit:
        assert ours.meta.get("assumed_microvolts"), "expected the microvolt assumption to fire"
        b = b * 1e-6
    else:
        assert not ours.meta.get("assumed_microvolts"), "unit was declared; should not assume"

    scale = max(float(np.abs(b).max()), 1e-30)
    assert np.abs(a - b).max() / scale < 1e-9, "sample values disagree with MNE"


@pytest.mark.parametrize("name,path,blank_unit", CASES, ids=[c[0] for c in CASES])
def test_amplitudes_are_physically_plausible(name, path, blank_unit):
    """Guards the unit assumption: scalp EEG cannot be volts."""
    if not path.exists():
        pytest.skip(f"dataset not present: {path}")

    ours = read_edf(path)
    median = ours.meta.get("median_abs_amplitude_v")
    if median is None or median == 0:
        pytest.skip("no EEG channels with signal")

    # Real scalp EEG sits in the microvolt range; allow a wide margin either way
    # but reject the volt-scale misreading that a blank unit field invites.
    assert 1e-9 < median < 1e-2, f"implausible EEG amplitude {median:g} V -- unit misread?"


def test_annotations_recover_cued_events():
    """Dataset 01's EDF annotations must carry the 20 cued task beeps."""
    path = D01 / "sub-01" / "sub-01_task-EB_acq-DSI_eeg.edf"
    if not path.exists():
        pytest.skip("dataset not present")

    ann = read_edf(path).meta["annotations"]
    beeps = [a for a in ann if a.description.endswith("Number_02")]

    assert len(beeps) == 20, f"expected 20 cued beeps, got {len(beeps)}"
    gaps = np.diff([a.onset for a in beeps])
    assert np.allclose(gaps, 3.0, atol=0.05), f"beeps should be 3 s apart, got {gaps[:5]}"


def test_bytes_and_path_agree():
    """The browser hands over bytes; the CLI hands over a path."""
    path = D01 / "sub-01" / "sub-01_task-EB_acq-MW2_eeg.edf"
    if not path.exists():
        pytest.skip("dataset not present")

    from_path = read_edf(path)
    from_bytes = read_edf(path.read_bytes())

    np.testing.assert_array_equal(from_path.data, from_bytes.data)
    assert from_path.ch_names == from_bytes.ch_names
    assert from_path.sfreq == from_bytes.sfreq
