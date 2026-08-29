"""Command-line interface.

    eeg-scope recording.edf
    eeg-scope data/ --json report.json

Exists for the cases the browser cannot cover: formats that need MNE (`.fif`,
BrainVision, BIDS trees), files large enough to be awkward in a tab, and batch
runs over a whole study.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .pipeline import analyse
from .readers import SUPPORTED, UnsupportedFormat

# Extensions worth trying when handed a directory.
SCAN_EXTS = {".edf", ".bdf", ".set", ".fif", ".vhdr"}

BAR_WIDTH = 28


def _bar(fraction: float, width: int = BAR_WIDTH) -> str:
    filled = int(round(max(0.0, min(1.0, fraction)) * width))
    return "#" * filled + "." * (width - filled)


def _load(path: Path, use_mne: bool):
    """Read via eegscope, falling back to MNE for formats it does not cover."""
    try:
        return analyse(path)
    except UnsupportedFormat:
        if not use_mne:
            raise
        from labio.mne_reader import read_with_mne

        return analyse(read_with_mne(path))


def _report(path: Path, analysis, verbose: bool) -> None:
    q = analysis.quality
    info = analysis.as_dict()["file"]

    print(f"\n{path.name}")
    print("-" * max(len(path.name), 60))
    print(
        f"  {info['n_channels_analysed']}/{info['n_channels_total']} channels  "
        f"{info['sfreq']:g} Hz  {q.duration_s:.0f}s  ({info['format']})"
    )
    print()
    print(f"  SCORE {q.score:5.1f}  grade {q.grade}")
    print(f"  {q.verdict}")
    print(
        f"  Usable: {q.usable_seconds:.0f}s of {q.duration_s:.0f}s "
        f"({q.usable_fraction:.0%})"
    )
    print()

    for c in q.components:
        if c.skipped:
            print(f"    {'n/a':>6}  {c.label:<22}  {c.explanation}")
        else:
            print(
                f"    {-c.penalty:6.1f}  {c.label:<22}  "
                f"{_bar(c.penalty / c.weight if c.weight else 0)}"
            )
            if verbose:
                print(f"            {c.explanation}")

    if q.bad_channels:
        print(f"\n  Bad channels: {', '.join(q.bad_channels)}")
    for w in q.warnings:
        print(f"\n  ! {w}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="eeg-scope",
        description="Check EEG signal quality: artifacts, bad channels, usable data.",
    )
    ap.add_argument("path", type=Path, help="an EEG file, or a directory to scan")
    ap.add_argument("--json", type=Path, help="write the full report as JSON")
    ap.add_argument("-v", "--verbose", action="store_true", help="explain every component")
    ap.add_argument(
        "--no-mne",
        action="store_true",
        help="do not fall back to MNE for formats eegscope cannot read itself",
    )
    args = ap.parse_args(argv)

    if not args.path.exists():
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 2

    if args.path.is_dir():
        files = sorted(
            p for p in args.path.rglob("*") if p.suffix.lower() in SCAN_EXTS
        )
        if not files:
            print(
                f"error: no EEG files under {args.path} "
                f"(looked for {', '.join(sorted(SCAN_EXTS))})",
                file=sys.stderr,
            )
            return 2
    else:
        files = [args.path]

    reports: dict[str, dict] = {}
    failures = 0

    for path in files:
        try:
            analysis = _load(path, use_mne=not args.no_mne)
        except UnsupportedFormat as exc:
            print(f"\n{path.name}\n  skipped: {exc}", file=sys.stderr)
            failures += 1
            continue
        except Exception as exc:
            print(f"\n{path.name}\n  failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            failures += 1
            continue

        _report(path, analysis, args.verbose)
        reports[str(path)] = analysis.as_dict()

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(reports, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json}")

    if len(files) > 1:
        scored = [
            r["quality"]["score"] for r in reports.values() if r.get("quality")
        ]
        if scored:
            print(
                f"\n{len(scored)} file(s) scored, mean {sum(scored) / len(scored):.1f}"
                + (f", {failures} failed" if failures else "")
            )

    return 1 if failures and not reports else 0


if __name__ == "__main__":
    raise SystemExit(main())
