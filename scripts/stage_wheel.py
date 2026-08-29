"""Build the eegscope wheel and stage it for the website under a hashed name.

Two problems this solves, both of which bit once already.

The wheel is served with a one year immutable cache header, which is correct
only if the URL changes when the contents change. Under a fixed filename a
returning visitor keeps running whatever wheel they downloaded first, however
old. Putting the content hash in the filename makes the URL change on every
real change, so the caching is safe.

The second is staleness at deploy time: it is easy to edit ``eegscope`` and
forget that the browser runs a separately built copy. ``tests/test_wheel_fresh.py``
fails when that happens, and this script is the fix it points at.

    python scripts/stage_wheel.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
STAGE = ROOT / "web" / "public" / "wheels"
POINTER = STAGE / "current.json"


def main() -> int:
    print("Building the wheel")
    result = subprocess.run(
        ["uv", "build", "--wheel"], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout, result.stderr, file=sys.stderr)
        return result.returncode

    built = sorted(DIST.glob("eeg_artifact_scope-*.whl"), key=lambda p: p.stat().st_mtime)
    if not built:
        print("no wheel produced in dist/", file=sys.stderr)
        return 1
    wheel = built[-1]

    digest = hashlib.sha256(wheel.read_bytes()).hexdigest()[:12]

    # The hash goes in the build-tag slot, not the version slot. A wheel
    # filename is name-version-[buildtag-]python-abi-platform.whl, the version
    # has to parse as a real version, and the build tag has to start with a
    # digit. Putting a bare hash where the version goes makes micropip reject
    # the file with InvalidWheelFilename, which is how this was found.
    stem = wheel.name.split("-py3-none-any.whl")[0]      # eeg_artifact_scope-0.1.0
    name = f"{stem}-0{digest}-py3-none-any.whl"

    STAGE.mkdir(parents=True, exist_ok=True)
    # Only one wheel is ever staged, so the page cannot serve an ambiguous set.
    for old in STAGE.glob("*.whl"):
        if old.name != name:
            old.unlink()
    shutil.copy2(wheel, STAGE / name)

    POINTER.write_text(
        json.dumps({"url": f"/wheels/{name}", "sha256_12": digest}, indent=1),
        encoding="utf-8",
    )

    size = (STAGE / name).stat().st_size / 1024
    print(f"Staged {name} ({size:.0f} KB)")
    print(f"Pointer {POINTER.relative_to(ROOT)} -> /wheels/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
