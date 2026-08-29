"""The wheel the browser runs must match the source the tests check.

This exists because it silently broke once. The percentile fix to the head-wide
statistic landed in ``eegscope`` and the site kept serving a wheel built before
it, so the browser scored a 20-electrode recording 51 while the same file
scored 77 locally. Nothing failed, nothing warned, and the website quietly
disagreed with its own published numbers.

Rebuild with::

    uv build --wheel && cp dist/*.whl web/public/wheels/
"""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "eegscope"
WHEEL_DIR = ROOT / "web" / "public" / "wheels"

REBUILD = "uv build --wheel && cp dist/*.whl web/public/wheels/"


def _digest(data: bytes) -> str:
    # Normalise line endings so a checkout on another platform still matches.
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()[:16]


def _wheel() -> Path:
    wheels = sorted(WHEEL_DIR.glob("*.whl"))
    if not wheels:
        pytest.skip(f"no wheel staged in {WHEEL_DIR}")
    if len(wheels) > 1:
        pytest.fail(
            f"{len(wheels)} wheels staged in web/public/wheels/, so the page cannot "
            f"know which one it is serving: {[w.name for w in wheels]}"
        )
    return wheels[0]


def test_wheel_matches_source():
    """Every eegscope module in the wheel is byte-identical to the source."""
    wheel = _wheel()
    source = {
        p.relative_to(ROOT).as_posix(): _digest(p.read_bytes())
        for p in SRC.rglob("*.py")
        if "__pycache__" not in p.parts
    }
    assert source, "no source modules found"

    with zipfile.ZipFile(wheel) as zf:
        packed = {
            name: _digest(zf.read(name))
            for name in zf.namelist()
            if name.startswith("eegscope/") and name.endswith(".py")
        }

    missing = sorted(set(source) - set(packed))
    extra = sorted(set(packed) - set(source))
    changed = sorted(k for k in set(source) & set(packed) if source[k] != packed[k])

    problems = []
    if missing:
        problems.append(f"in source but not in the wheel: {missing}")
    if extra:
        problems.append(f"in the wheel but not in source: {extra}")
    if changed:
        problems.append(f"different contents: {changed}")

    assert not problems, (
        f"The staged wheel is out of date with eegscope/.\n  "
        + "\n  ".join(problems)
        + f"\nThe browser would run different code from these tests. Rebuild:\n  {REBUILD}"
    )


def test_wheel_carries_the_detection_code():
    """A blunt check that the wheel is a real build and not an empty shell."""
    wheel = _wheel()
    with zipfile.ZipFile(wheel) as zf:
        names = set(zf.namelist())

    for required in (
        "eegscope/pipeline.py",
        "eegscope/score.py",
        "eegscope/web.py",
        "eegscope/detect/base.py",
        "eegscope/detect/blink.py",
        "eegscope/detect/muscle.py",
        "eegscope/readers/edf.py",
    ):
        assert required in names, f"{required} missing from the wheel. Rebuild:\n  {REBUILD}"
