"""The one entry point: bytes or a path in, a full quality report out.

This is what the browser worker calls and what the CLI calls, so both paths
are guaranteed to produce identical numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .detect.badchannel import detect_bad_channels
from .detect.base import BLINK, CARDIAC, DRIFT, LINE_NOISE, MUSCLE, POP, DetectorResult
from .detect.blink import detect_blinks
from .detect.cardiac import detect_cardiac
from .detect.drift import detect_drift, detect_pops
from .detect.linenoise import detect_line_noise
from .detect.muscle import detect_muscle
from .readers import load
from .recording import Recording
from .score import QualityReport, score_recording
from .triage import TriageReport, triage


@dataclass
class Analysis:
    """Everything the UI needs, in one object."""

    recording: Recording
    triaged: Recording
    triage_report: TriageReport
    results: dict[str, DetectorResult] = field(default_factory=dict)
    quality: QualityReport | None = None

    def as_dict(self) -> dict[str, Any]:
        rec, tri = self.recording, self.triaged
        return {
            "file": {
                "format": rec.source_format,
                "duration_s": round(rec.duration, 2),
                "sfreq": rec.sfreq,
                "n_channels_total": rec.n_channels,
                "n_channels_analysed": tri.n_channels,
                "channel_names": tri.ch_names,
                "assumed_microvolts": bool(rec.meta.get("assumed_microvolts")),
            },
            "triage": self.triage_report.as_dict(),
            "quality": self.quality.as_dict() if self.quality else None,
            "detectors": {
                k: v.as_dict(duration=rec.duration) for k, v in self.results.items()
            },
        }


def analyse(
    source,
    *,
    filename: str | None = None,
    include_cardiac: bool = True,
) -> Analysis:
    """Run the full pipeline.

    Parameters
    ----------
    source
        Path, or raw file bytes (what a browser upload gives us).
    filename
        Original name, used for format sniffing when ``source`` is bytes.
    """
    rec = source if isinstance(source, Recording) else load(source, filename=filename)
    triaged, tri_report = triage(rec)

    results: dict[str, DetectorResult] = {}

    if triaged.n_channels == 0:
        # Nothing analysable. Return an honest empty report rather than
        # crashing or, worse, scoring it as clean.
        quality = score_recording(rec, results, triage_warnings=tri_report.warnings)
        return Analysis(rec, triaged, tri_report, results, quality)

    # Blink detection prefers real EOG channels, which live on the untriaged
    # recording -- triage strips non-EEG. Hand it whichever has them.
    blink_input = rec if rec.picks("eog") else triaged
    results[BLINK] = detect_blinks(blink_input)

    results[MUSCLE] = detect_muscle(triaged)
    results[DRIFT] = detect_drift(triaged)
    results[POP] = detect_pops(triaged)
    results[LINE_NOISE] = detect_line_noise(triaged)
    if include_cardiac:
        cardiac_input = rec if rec.picks("ecg") else triaged
        results[CARDIAC] = detect_cardiac(cardiac_input)
    results["bad_channel"] = detect_bad_channels(triaged)

    quality = score_recording(triaged, results, triage_warnings=tri_report.warnings)
    return Analysis(rec, triaged, tri_report, results, quality)
