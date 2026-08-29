'use client';

import { useId, useMemo } from 'react';

/** Colour per artifact class. Shared by the timeline and every legend. */
export const KIND_COLOR: Record<string, string> = {
  blink: 'var(--accent)',
  muscle: 'var(--worst)',
  drift: 'var(--warn)',
  electrode_pop: 'var(--highlight)',
  cardiac: 'var(--good)',
  line_noise: 'var(--ink-3)',
};

export function scoreColor(score: number): string {
  if (score >= 90) return 'var(--good)';
  if (score >= 80) return 'var(--ok)';
  if (score >= 70) return 'var(--warn)';
  if (score >= 60) return 'var(--bad)';
  return 'var(--worst)';
}

/* ------------------------------------------------------------------ line */

export interface Series {
  label: string;
  color: string;
  x: number[];
  y: number[];
  dashed?: boolean;
}

export function LineChart({
  series,
  xLabel,
  yLabel,
  height = 260,
  yMin,
  yMax,
  markers = [],
  caption,
}: {
  series: Series[];
  xLabel: string;
  yLabel: string;
  height?: number;
  yMin?: number;
  yMax?: number;
  markers?: { x: number; label: string; color?: string }[];
  caption?: string;
}) {
  const id = useId();
  const W = 900;
  const pad = { l: 56, r: 16, t: 14, b: 40 };

  const bounds = useMemo(() => {
    const xs = series.flatMap((s) => s.x);
    const ys = series.flatMap((s) => s.y);
    const x0 = Math.min(...xs);
    const x1 = Math.max(...xs);
    const lo = yMin ?? Math.min(...ys);
    const hi = yMax ?? Math.max(...ys);
    const padY = (hi - lo) * 0.08 || 1;
    return { x0, x1, y0: lo - padY, y1: hi + padY };
  }, [series, yMin, yMax]);

  const sx = (v: number) =>
    pad.l + ((v - bounds.x0) / (bounds.x1 - bounds.x0 || 1)) * (W - pad.l - pad.r);
  const sy = (v: number) =>
    pad.t + (1 - (v - bounds.y0) / (bounds.y1 - bounds.y0 || 1)) * (height - pad.t - pad.b);

  const ticksX = niceTicks(bounds.x0, bounds.x1, 6);
  const ticksY = niceTicks(bounds.y0, bounds.y1, 5);

  return (
    <figure>
      <div className="scroll">
        <svg
          viewBox={`0 0 ${W} ${height}`}
          width="100%"
          style={{ minWidth: 460, display: 'block' }}
          role="img"
          aria-labelledby={`${id}-t`}
        >
          <title id={`${id}-t`}>
            {caption ?? `${yLabel} against ${xLabel}`}
          </title>

          {ticksY.map((t) => (
            <g key={`y${t}`}>
              <line
                x1={pad.l}
                x2={W - pad.r}
                y1={sy(t)}
                y2={sy(t)}
                stroke="var(--line-soft)"
              />
              <text
                x={pad.l - 8}
                y={sy(t) + 4}
                textAnchor="end"
                fontSize="11"
                fill="var(--ink-3)"
                fontFamily="var(--mono)"
              >
                {fmt(t)}
              </text>
            </g>
          ))}

          {ticksX.map((t) => (
            <text
              key={`x${t}`}
              x={sx(t)}
              y={height - pad.b + 17}
              textAnchor="middle"
              fontSize="11"
              fill="var(--ink-3)"
              fontFamily="var(--mono)"
            >
              {fmt(t)}
            </text>
          ))}

          {markers.map((m, i) => (
            <g key={i}>
              <line
                x1={sx(m.x)}
                x2={sx(m.x)}
                y1={pad.t}
                y2={height - pad.b}
                stroke={m.color ?? 'var(--highlight)'}
                strokeDasharray="4 4"
                strokeWidth="1.2"
              />
              <text
                x={sx(m.x) + 5}
                y={pad.t + 12}
                fontSize="10.5"
                fill={m.color ?? 'var(--highlight)'}
                fontFamily="var(--mono)"
              >
                {m.label}
              </text>
            </g>
          ))}

          <line
            x1={pad.l}
            x2={W - pad.r}
            y1={height - pad.b}
            y2={height - pad.b}
            stroke="var(--line)"
          />

          {series.map((s) => (
            <path
              key={s.label}
              d={s.x
                .map((xv, i) => `${i ? 'L' : 'M'}${sx(xv).toFixed(1)},${sy(s.y[i]).toFixed(1)}`)
                .join('')}
              fill="none"
              stroke={s.color}
              strokeWidth="1.9"
              strokeDasharray={s.dashed ? '5 4' : undefined}
              strokeLinejoin="round"
            />
          ))}

          <text
            x={(W - pad.l) / 2 + pad.l / 2}
            y={height - 4}
            textAnchor="middle"
            fontSize="11.5"
            fill="var(--ink-3)"
          >
            {xLabel}
          </text>
          <text
            transform={`rotate(-90 12 ${height / 2})`}
            x="12"
            y={height / 2}
            textAnchor="middle"
            fontSize="11.5"
            fill="var(--ink-3)"
          >
            {yLabel}
          </text>
        </svg>
      </div>

      {series.length > 1 && (
        <div
          style={{
            display: 'flex',
            gap: 16,
            flexWrap: 'wrap',
            marginTop: 8,
            fontSize: 13,
            color: 'var(--ink-2)',
          }}
        >
          {series.map((s) => (
            <span key={s.label} style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>
              <span
                style={{
                  width: 16,
                  height: 3,
                  background: s.color,
                  borderRadius: 2,
                  display: 'inline-block',
                }}
              />
              {s.label}
            </span>
          ))}
        </div>
      )}

      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

/* ------------------------------------------------------------- band chart */

/** A mean line with an interquartile band behind it. */
export function BandChart({
  x,
  mean,
  lo,
  hi,
  color,
  xLabel,
  yLabel,
  height = 240,
  caption,
}: {
  x: number[];
  mean: number[];
  lo: number[];
  hi: number[];
  color: string;
  xLabel: string;
  yLabel: string;
  height?: number;
  caption?: string;
}) {
  const id = useId();
  const W = 900;
  const pad = { l: 56, r: 16, t: 14, b: 40 };

  const x0 = Math.min(...x);
  const x1 = Math.max(...x);
  const y0 = Math.min(...lo);
  const y1 = Math.max(...hi);
  const padY = (y1 - y0) * 0.08 || 1;

  const sx = (v: number) => pad.l + ((v - x0) / (x1 - x0 || 1)) * (W - pad.l - pad.r);
  const sy = (v: number) =>
    pad.t + (1 - (v - (y0 - padY)) / (y1 + padY - (y0 - padY) || 1)) * (height - pad.t - pad.b);

  const area =
    x.map((xv, i) => `${i ? 'L' : 'M'}${sx(xv).toFixed(1)},${sy(hi[i]).toFixed(1)}`).join('') +
    x
      .map((xv, i) => `L${sx(x[x.length - 1 - i]).toFixed(1)},${sy(lo[lo.length - 1 - i]).toFixed(1)}`)
      .join('') +
    'Z';

  const ticksY = niceTicks(y0 - padY, y1 + padY, 5);
  const ticksX = niceTicks(x0, x1, 6);

  return (
    <figure>
      <div className="scroll">
        <svg viewBox={`0 0 ${W} ${height}`} width="100%" style={{ minWidth: 460, display: 'block' }}
             role="img" aria-labelledby={`${id}-t`}>
          <title id={`${id}-t`}>{caption ?? `${yLabel} against ${xLabel}`}</title>

          {ticksY.map((t) => (
            <g key={t}>
              <line x1={pad.l} x2={W - pad.r} y1={sy(t)} y2={sy(t)} stroke="var(--line-soft)" />
              <text x={pad.l - 8} y={sy(t) + 4} textAnchor="end" fontSize="11"
                    fill="var(--ink-3)" fontFamily="var(--mono)">{fmt(t)}</text>
            </g>
          ))}
          {ticksX.map((t) => (
            <text key={t} x={sx(t)} y={height - pad.b + 17} textAnchor="middle" fontSize="11"
                  fill="var(--ink-3)" fontFamily="var(--mono)">{fmt(t)}</text>
          ))}

          <path d={area} fill={color} opacity="0.16" />
          <path
            d={x.map((xv, i) => `${i ? 'L' : 'M'}${sx(xv).toFixed(1)},${sy(mean[i]).toFixed(1)}`).join('')}
            fill="none" stroke={color} strokeWidth="2.1" strokeLinejoin="round"
          />
          <line x1={pad.l} x2={W - pad.r} y1={sy(0)} y2={sy(0)} stroke="var(--line)" strokeDasharray="2 3" />

          <text x={(W - pad.l) / 2 + pad.l / 2} y={height - 4} textAnchor="middle"
                fontSize="11.5" fill="var(--ink-3)">{xLabel}</text>
          <text transform={`rotate(-90 12 ${height / 2})`} x="12" y={height / 2}
                textAnchor="middle" fontSize="11.5" fill="var(--ink-3)">{yLabel}</text>
        </svg>
      </div>
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

/* ------------------------------------------------------------ trace strip */

export function TraceStrip({
  channels,
  durationS,
  height = 34,
  color = 'var(--accent)',
  caption,
}: {
  channels: { name: string; minmax: [number, number][] }[];
  durationS: number;
  height?: number;
  color?: string;
  caption?: string;
}) {
  const id = useId();
  const W = 900;
  const H = channels.length * height;

  const peak = useMemo(() => {
    let m = 0;
    for (const c of channels) for (const [a, b] of c.minmax) m = Math.max(m, Math.abs(a), Math.abs(b));
    return m || 1;
  }, [channels]);

  return (
    <figure>
      <div className="scroll">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: 460, display: 'block' }}
             role="img" aria-labelledby={`${id}-t`}>
          <title id={`${id}-t`}>{caption ?? 'EEG traces'}</title>
          {channels.map((c, i) => {
            const y0 = i * height + height / 2;
            const n = c.minmax.length;
            const d = c.minmax
              .map(([lo, hi], k) => {
                const x = (k / Math.max(1, n - 1)) * W;
                const a = y0 - (hi / peak) * (height / 2 - 3);
                const b = y0 - (lo / peak) * (height / 2 - 3);
                return `M${x.toFixed(2)},${a.toFixed(2)}L${x.toFixed(2)},${b.toFixed(2)}`;
              })
              .join('');
            return (
              <g key={c.name}>
                {i > 0 && <line x1="0" x2={W} y1={i * height} y2={i * height} stroke="var(--line-soft)" />}
                <path d={d} stroke={color} strokeWidth="0.75" fill="none" opacity="0.9" />
                <text x="5" y={i * height + 12} fontSize="10" fill="var(--ink-3)"
                      fontFamily="var(--mono)"
                      style={{ paintOrder: 'stroke', stroke: 'var(--panel)', strokeWidth: 3 }}>
                  {c.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11,
                    color: 'var(--ink-3)', fontFamily: 'var(--mono)', marginTop: 3 }}>
        <span>0 s</span>
        <span>peak {peak.toFixed(0)} µV</span>
        <span>{durationS.toFixed(0)} s</span>
      </div>
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

/* ----------------------------------------------------------------- bars */

export function BarChart({
  items,
  unit = '',
  height = 30,
  caption,
}: {
  items: { label: string; value: number; color?: string; note?: string }[];
  unit?: string;
  height?: number;
  caption?: string;
}) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <figure>
      <div>
        {items.map((it) => (
          <div key={it.label} style={{ marginBottom: 10 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13.5, marginBottom: 3 }}>
              <span>{it.label}</span>
              <span style={{ fontFamily: 'var(--mono)', color: 'var(--ink-2)' }}>
                {fmt(it.value)}{unit}
              </span>
            </div>
            <div style={{ height: 9, background: 'var(--panel-2)', borderRadius: 5, overflow: 'hidden' }}>
              <div style={{ width: `${(it.value / max) * 100}%`, height: '100%',
                            background: it.color ?? 'var(--accent)', borderRadius: 5 }} />
            </div>
            {it.note && (
              <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 2 }}>{it.note}</div>
            )}
          </div>
        ))}
      </div>
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

/* ---------------------------------------------------------------- helpers */

function niceTicks(lo: number, hi: number, count: number): number[] {
  if (!isFinite(lo) || !isFinite(hi) || hi <= lo) return [lo];
  const raw = (hi - lo) / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) out.push(round(v));
  return out;
}

function round(v: number): number {
  return Math.abs(v) < 1e-9 ? 0 : parseFloat(v.toPrecision(12));
}

function fmt(v: number): string {
  if (v === 0) return '0';
  const a = Math.abs(v);
  if (a >= 1000) return v.toLocaleString('en-US');
  if (a >= 10) return v.toFixed(0);
  if (a >= 1) return v.toFixed(1);
  return v.toFixed(2);
}
