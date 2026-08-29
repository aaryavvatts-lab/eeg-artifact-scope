'use client';

import { useMemo } from 'react';
import type { Analysis, ArtifactEvent, DetectorOut } from '@/lib/types';

/** Colour per artifact class, reused by the timeline and the legend. */
export const KIND_COLOR: Record<string, string> = {
  blink: '#6ea8fe',
  muscle: '#f87171',
  drift: '#fbbf24',
  electrode_pop: '#c084fc',
  cardiac: '#4ade80',
  line_noise: '#94a3b8',
};

export function scoreColor(score: number): string {
  if (score >= 90) return 'var(--good)';
  if (score >= 80) return 'var(--ok)';
  if (score >= 70) return 'var(--warn)';
  if (score >= 60) return 'var(--bad)';
  return 'var(--worst)';
}

/** Circular score gauge. */
export function Gauge({ score, grade }: { score: number; grade: string }) {
  const r = 56;
  const c = 2 * Math.PI * r;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * c;
  const color = scoreColor(score);
  return (
    <div className="gauge">
      <svg width="132" height="132" viewBox="0 0 132 132" aria-hidden="true">
        <circle cx="66" cy="66" r={r} fill="none" stroke="var(--panel-2)" strokeWidth="11" />
        <circle
          cx="66"
          cy="66"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${c - filled}`}
          transform="rotate(-90 66 66)"
        />
      </svg>
      <div className="val">
        <span className="num" style={{ color }}>{score.toFixed(0)}</span>
        <span className="grade">grade {grade}</span>
      </div>
    </div>
  );
}

/**
 * Where the artifacts are in time.
 *
 * One lane per artifact class so overlapping events stay readable — a jaw
 * clench and a blink at the same instant are two different problems.
 */
export function Timeline({ analysis }: { analysis: Analysis }) {
  const duration = analysis.file.duration_s;
  const lanes = useMemo(() => {
    const out: { kind: string; label: string; events: ArtifactEvent[] }[] = [];
    for (const d of Object.values(analysis.detectors) as DetectorOut[]) {
      if (d.skipped_reason || !d.events?.length) continue;
      out.push({ kind: d.kind, label: d.label, events: d.events });
    }
    return out;
  }, [analysis]);

  if (!lanes.length) {
    return <p className="sub">No timed artifacts were detected.</p>;
  }

  const W = 1000;
  const laneH = 18;
  const gap = 6;
  const H = lanes.length * (laneH + gap);

  return (
    <div className="scroll">
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: 520 }} role="img"
           aria-label="Artifact occurrences over time">
        {lanes.map((lane, i) => {
          const y = i * (laneH + gap);
          return (
            <g key={lane.kind}>
              <rect x="0" y={y} width={W} height={laneH} rx="4" fill="var(--panel-2)" />
              {lane.events.map((e, j) => {
                const x = (e.onset / duration) * W;
                const w = Math.max(1.5, (e.duration / duration) * W);
                return (
                  <rect
                    key={j}
                    x={x}
                    y={y}
                    width={w}
                    height={laneH}
                    rx="2"
                    fill={KIND_COLOR[lane.kind] ?? '#888'}
                    opacity={0.45 + 0.55 * e.severity}
                  >
                    <title>{`${lane.label} at ${e.onset.toFixed(1)}s (${e.duration.toFixed(2)}s)`}</title>
                  </rect>
                );
              })}
              <text x="6" y={y + laneH - 5} fontSize="10.5" fill="var(--ink-dim)"
                    style={{ paintOrder: 'stroke', stroke: 'var(--panel-2)', strokeWidth: 3 }}>
                {lane.label} · {lane.events.length}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="stats" style={{ marginTop: 8, fontSize: 12 }}>
        <span>0s</span>
        <span style={{ marginLeft: 'auto' }}>{duration.toFixed(0)}s</span>
      </div>
    </div>
  );
}

/** Decimated raw traces, min/max per pixel column so spikes survive. */
export function Traces({ analysis }: { analysis: Analysis }) {
  const p = analysis.preview;
  if (!p?.channels?.length) return null;

  const W = 1000;
  const rowH = 30;
  const H = p.channels.length * rowH;

  // One shared scale across channels, so relative amplitude stays readable.
  const peak = useMemo(() => {
    let m = 0;
    for (const ch of p.channels) {
      for (const [lo, hi] of ch.minmax) {
        m = Math.max(m, Math.abs(lo), Math.abs(hi));
      }
    }
    return m || 1;
  }, [p]);

  return (
    <div className="scroll">
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: 520 }} role="img"
           aria-label="Raw EEG traces">
        {p.channels.map((ch, i) => {
          const y0 = i * rowH + rowH / 2;
          const n = ch.minmax.length;
          const path = ch.minmax
            .map(([lo, hi], k) => {
              const x = (k / Math.max(1, n - 1)) * W;
              const a = y0 - (hi / peak) * (rowH / 2 - 2);
              const b = y0 - (lo / peak) * (rowH / 2 - 2);
              return `M${x.toFixed(2)},${a.toFixed(2)}L${x.toFixed(2)},${b.toFixed(2)}`;
            })
            .join('');
          return (
            <g key={ch.name}>
              <path d={path} stroke="var(--accent)" strokeWidth="0.7" fill="none" opacity="0.85" />
              <text x="4" y={y0 - rowH / 2 + 10} fontSize="9.5" fill="var(--ink-faint)"
                    style={{ paintOrder: 'stroke', stroke: 'var(--panel)', strokeWidth: 3 }}>
                {ch.name}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="note" style={{ marginTop: 6 }}>
        Peak amplitude {peak.toFixed(0)} µV. Showing {p.n_shown} of {p.n_total} channels,
        drawn as min/max per column so brief spikes stay visible.
      </p>
    </div>
  );
}

/** Average power spectrum. */
export function Spectrum({ analysis }: { analysis: Analysis }) {
  const psd = analysis.psd;
  if (!psd?.freqs?.length) return null;

  const W = 1000;
  const H = 220;
  const pad = { l: 42, r: 10, t: 10, b: 26 };

  const fMax = psd.freqs[psd.freqs.length - 1];
  const dbMin = Math.min(...psd.db);
  const dbMax = Math.max(...psd.db);
  const span = Math.max(1, dbMax - dbMin);

  const x = (f: number) => pad.l + (f / fMax) * (W - pad.l - pad.r);
  const y = (d: number) => pad.t + (1 - (d - dbMin) / span) * (H - pad.t - pad.b);

  const path = psd.freqs
    .map((f, i) => `${i ? 'L' : 'M'}${x(f).toFixed(1)},${y(psd.db[i]).toFixed(1)}`)
    .join('');

  const lineHz = analysis.detectors?.line_noise?.detail?.line_frequency_hz as number | undefined;
  const ticks = [0, 10, 20, 30, 40, 60, 80, 100, 120].filter((t) => t <= fMax);

  return (
    <div className="scroll">
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ minWidth: 520 }} role="img"
           aria-label="Average power spectrum">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} y1={pad.t} x2={x(t)} y2={H - pad.b} stroke="var(--line)" strokeWidth="1" />
            <text x={x(t)} y={H - 8} fontSize="10" fill="var(--ink-faint)" textAnchor="middle">{t}</text>
          </g>
        ))}
        {lineHz && lineHz <= fMax && (
          <line x1={x(lineHz)} y1={pad.t} x2={x(lineHz)} y2={H - pad.b}
                stroke="var(--worst)" strokeWidth="1" strokeDasharray="3 3" opacity="0.7" />
        )}
        <path d={path} stroke="var(--accent)" strokeWidth="1.6" fill="none" />
        <text x={4} y={pad.t + 8} fontSize="10" fill="var(--ink-faint)">dB</text>
        <text x={W / 2} y={H - 8} fontSize="10" fill="var(--ink-faint)" textAnchor="middle"
              opacity="0">Hz</text>
      </svg>
      <p className="note" style={{ marginTop: 4 }}>
        Frequency (Hz). {lineHz ? `Dashed line marks ${lineHz} Hz mains.` : ''}
      </p>
    </div>
  );
}
