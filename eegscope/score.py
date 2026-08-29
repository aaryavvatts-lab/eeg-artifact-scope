"""Turn detector output into a quality score a researcher can act on.

Design rule: **the breakdown matters more than the number.** A bare 0-100 with
no provenance is not actionable and invites false confidence, so every
component states what it measured, what it cost, and why.

The headline number people actually need is not the score -- it is
``usable_seconds``: how much of the recording survives once contaminated spans
are removed. That is the answer to "do I have enough data?"
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .detect.base import BLINK, CARDIAC, DRIFT, LINE_NOISE, MUSCLE, POP, DetectorResult
from .recording import Recording

# How many points each artifact class can remove from 100. Weights reflect how
# much each one actually threatens an analysis: muscle is the most destructive
# because it is broadband and overlaps real gamma/beta, blinks are large but
# stereotyped and removable by ICA, cardiac is small and largely benign.
WEIGHTS = {
    MUSCLE: 30.0,
    BLINK: 22.0,
    DRIFT: 16.0,
    POP: 12.0,
    LINE_NOISE: 12.0,
    CARDIAC: 4.0,
}
BAD_CHANNEL_WEIGHT = 20.0

# Contaminated fraction at which a class costs its full weight.
SATURATION = {
    MUSCLE: 0.35,
    BLINK: 0.35,
    DRIFT: 0.30,
    POP: 0.10,
    CARDIAC: 0.60,
}

# dB above local baseline at which line noise costs its full weight.
LINE_NOISE_SATURATION_DB = 20.0

GRADES = [(90, "A"), (80, "B"), (70, "C"), (60, "D"), (0, "F")]


@dataclass
class ScoreComponent:
    kind: str
    label: str
    penalty: float          # points removed, 0..weight
    weight: float
    measured: float         # the raw quantity behind the penalty
    unit: str
    explanation: str
    skipped: bool = False

    def as_dict(self) -> dict:
        return {
            "kind": self.kind,
            "label": self.label,
            "penalty": round(self.penalty, 2),
            "weight": self.weight,
            "measured": round(self.measured, 4),
            "unit": self.unit,
            "explanation": self.explanation,
            "skipped": self.skipped,
        }


@dataclass
class QualityReport:
    score: float
    grade: str
    verdict: str
    duration_s: float
    usable_seconds: float
    contaminated_seconds: float
    components: list[ScoreComponent] = field(default_factory=list)
    bad_channels: list[str] = field(default_factory=list)
    n_channels: int = 0
    warnings: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def usable_fraction(self) -> float:
        return self.usable_seconds / self.duration_s if self.duration_s else 0.0

    def as_dict(self) -> dict:
        return {
            "score": round(self.score, 1),
            "grade": self.grade,
            "verdict": self.verdict,
            "duration_s": round(self.duration_s, 2),
            "usable_seconds": round(self.usable_seconds, 2),
            "usable_fraction": round(self.usable_fraction, 4),
            "contaminated_seconds": round(self.contaminated_seconds, 2),
            "components": [c.as_dict() for c in self.components],
            "bad_channels": self.bad_channels,
            "n_channels": self.n_channels,
            "warnings": self.warnings,
            "skipped_checks": self.skipped,
        }


def _union_seconds(results: list[DetectorResult]) -> float:
    """Total wall-clock time covered by any event, counting overlaps once."""
    spans: list[tuple[float, float]] = []
    for r in results:
        spans.extend((e.onset, e.offset) for e in r.events)
    if not spans:
        return 0.0
    spans.sort()
    total = 0.0
    cur_s, cur_e = spans[0]
    for s, e in spans[1:]:
        if s > cur_e:
            total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    return total + (cur_e - cur_s)


def _grade(score: float) -> str:
    for cutoff, letter in GRADES:
        if score >= cutoff:
            return letter
    return "F"


def _verdict(score: float, usable_fraction: float, dominant: str | None) -> str:
    if score >= 90:
        return "Clean. Suitable for analysis as-is."
    if score >= 80:
        return f"Good. Some {dominant or 'artifact'} contamination, but most of the recording is usable."
    if score >= 70:
        return (
            f"Usable with cleaning. {dominant or 'Artifact'} contamination is significant; "
            f"about {usable_fraction:.0%} of the recording survives rejection."
        )
    if score >= 60:
        return (
            f"Marginal. Heavy {dominant or 'artifact'} contamination leaves roughly "
            f"{usable_fraction:.0%} usable. Consider re-recording."
        )
    return (
        f"Poor. {dominant or 'Artifact'} contamination dominates; only about "
        f"{usable_fraction:.0%} of the recording is usable. Re-record if possible."
    )


def score_recording(
    rec: Recording,
    results: dict[str, DetectorResult],
    *,
    triage_warnings: list[str] | None = None,
) -> QualityReport:
    """Combine detector results into a single report.

    ``results`` maps artifact kind -> DetectorResult, plus an optional
    ``"bad_channel"`` entry.
    """
    duration = rec.duration
    components: list[ScoreComponent] = []
    skipped: list[str] = []
    warnings = list(triage_warnings or [])

    timed = [r for k, r in results.items() if k != "bad_channel" and r.ok]
    contaminated = _union_seconds(timed)

    for kind, weight in WEIGHTS.items():
        r = results.get(kind)
        if r is None:
            continue

        if not r.ok:
            # A check that could not run is not a pass. Say so rather than
            # quietly awarding full marks.
            skipped.append(f"{r.kind}: {r.skipped_reason}")
            components.append(
                ScoreComponent(
                    kind=kind,
                    label=r.as_dict()["label"],
                    penalty=0.0,
                    weight=weight,
                    measured=0.0,
                    unit="",
                    explanation=f"Not assessed - {r.skipped_reason}.",
                    skipped=True,
                )
            )
            continue

        if kind == LINE_NOISE:
            db = float(r.detail.get("median_db", 0.0))
            frac = float(np.clip(db / LINE_NOISE_SATURATION_DB, 0.0, 1.0))
            penalty = weight * frac
            n_aff = r.detail.get("n_affected", 0)
            f0 = r.detail.get("line_frequency_hz")
            components.append(
                ScoreComponent(
                    kind=kind,
                    label="Mains line noise",
                    penalty=penalty,
                    weight=weight,
                    measured=db,
                    unit="dB",
                    explanation=(
                        f"{f0:.0f} Hz mains sits {db:.1f} dB above the surrounding "
                        f"spectrum on {n_aff} channel(s)."
                        if n_aff
                        else f"No meaningful {f0:.0f} Hz mains contamination."
                    ),
                )
            )
            continue

        frac = min(1.0, r.contaminated_seconds() / duration) if duration else 0.0
        sat = SATURATION.get(kind, 0.35)
        penalty = weight * float(np.clip(frac / sat, 0.0, 1.0))
        label = r.as_dict()["label"]
        per_min = r.rate_per_minute(duration)

        explanation = (
            f"{r.n_events} event(s), {per_min:.1f}/min, covering {frac:.1%} of the recording."
        )
        if kind == CARDIAC and not r.detail.get("used_real_ecg", False):
            explanation += " Inferred without an ECG channel, so treat as indicative."

        components.append(
            ScoreComponent(
                kind=kind,
                label=label,
                penalty=penalty,
                weight=weight,
                measured=frac,
                unit="fraction of recording",
                explanation=explanation,
            )
        )

    # -- bad channels ------------------------------------------------------
    bad_names: list[str] = []
    bc = results.get("bad_channel")
    if bc is not None and bc.ok:
        bad_names = list(bc.detail.get("bad_channels", []))
        n_total = max(1, int(bc.detail.get("n_total", rec.n_channels)))
        frac_bad = len(bad_names) / n_total
        penalty = BAD_CHANNEL_WEIGHT * float(np.clip(frac_bad / 0.25, 0.0, 1.0))
        components.append(
            ScoreComponent(
                kind="bad_channel",
                label="Bad channels",
                penalty=penalty,
                weight=BAD_CHANNEL_WEIGHT,
                measured=frac_bad,
                unit="fraction of channels",
                explanation=(
                    f"{len(bad_names)} of {n_total} channels failed quality checks: "
                    f"{', '.join(bad_names[:6])}"
                    + ("..." if len(bad_names) > 6 else "")
                    if bad_names
                    else f"All {n_total} channels passed."
                ),
            )
        )
        note = bc.detail.get("checks_skipped_note")
        if note:
            warnings.append(note)
    elif bc is not None:
        skipped.append(f"bad_channel: {bc.skipped_reason}")

    total_penalty = sum(c.penalty for c in components)
    score = float(np.clip(100.0 - total_penalty, 0.0, 100.0))

    scored = [c for c in components if not c.skipped and c.penalty > 0]
    dominant = max(scored, key=lambda c: c.penalty).label.lower() if scored else None

    usable = max(0.0, duration - contaminated)

    return QualityReport(
        score=score,
        grade=_grade(score),
        verdict=_verdict(score, usable / duration if duration else 0.0, dominant),
        duration_s=duration,
        usable_seconds=usable,
        contaminated_seconds=contaminated,
        components=sorted(components, key=lambda c: -c.penalty),
        bad_channels=bad_names,
        n_channels=rec.n_channels,
        warnings=warnings,
        skipped=skipped,
    )
