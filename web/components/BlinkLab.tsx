'use client';

import { useEffect, useMemo, useState } from 'react';
import { BandChart, LineChart, TraceStrip } from '@/components/Viz';

interface DeviceShape {
  label: string;
  channel: string;
  tier: string;
  channels: number;
  n_blinks: number;
  mean: number[];
  p25: number[];
  p75: number[];
  peak_uv: number;
  rest_rms_uv: number | null;
}

interface BlinkData {
  window_s: number;
  n_points: number;
  devices: Record<string, DeviceShape>;
}

interface Snippet {
  label: string;
  note: string;
  device: string;
  device_key: string;
  condition: string;
  source: string;
  t0: number;
  t1: number;
  duration_s: number;
  sfreq: number;
  channels: { name: string; minmax: [number, number][] }[];
  psd: { freqs: number[]; db: number[] };
  peak_uv: number;
  rms_uv: number;
}

/** The average blink shape, measured from real recordings. */
export function BlinkShape() {
  const [data, setData] = useState<BlinkData | null>(null);
  const [dev, setDev] = useState('Muse2');

  useEffect(() => {
    fetch('/data/blink-shapes.json')
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return <p className="note">Loading the measured blink shapes.</p>;

  const keys = Object.keys(data.devices);
  const d = data.devices[dev] ?? data.devices[keys[0]];
  if (!d) return null;

  const half = data.window_s / 2;
  const x = d.mean.map((_, i) => -half + (i / (d.mean.length - 1)) * data.window_s);

  return (
    <>
      <div className="chips" style={{ marginBottom: 14 }}>
        {keys.map((k) => (
          <button
            key={k}
            className="chip"
            aria-pressed={k === dev}
            onClick={() => setDev(k)}
          >
            {data.devices[k].label}
          </button>
        ))}
      </div>

      <BandChart
        x={x}
        mean={d.mean}
        lo={d.p25}
        hi={d.p75}
        color="var(--accent)"
        xLabel="Seconds either side of the blink"
        yLabel="Microvolts"
        caption={`Average of ${d.n_blinks} real blinks recorded at ${d.channel} on the ${d.label}. The band covers the middle half of them, so you can see how much blinks vary between people. Polarity depends on where the reference electrode sits, so each blink was flipped to match the sign of its own largest swing before averaging.`}
      />

      <div className="stats" style={{ marginTop: 6 }}>
        <div className="stat">
          <b>{d.peak_uv.toFixed(0)} µV</b>
          <span>height of the average blink</span>
        </div>
        <div className="stat">
          <b>{d.rest_rms_uv?.toFixed(0) ?? '?'} µV</b>
          <span>size of the ordinary signal at the same electrode</span>
        </div>
        <div className="stat">
          <b>{d.rest_rms_uv ? (d.peak_uv / d.rest_rms_uv).toFixed(1) : '?'}×</b>
          <span>how much bigger the blink is</span>
        </div>
        <div className="stat">
          <b>{d.n_blinks}</b>
          <span>blinks averaged, {d.channels} electrode{d.channels === 1 ? '' : 's'}</span>
        </div>
      </div>
    </>
  );
}

/**
 * Alpha rhythm against a blink, drawn to scale.
 *
 * The point is the scale, not the shapes. People know a blink is "big" and it
 * still surprises them how completely it swamps the rhythm they were after.
 */
export function BuriedAlpha() {
  const [alphaUv, setAlphaUv] = useState(20);
  const [blinkUv, setBlinkUv] = useState(150);
  const [showBlink, setShowBlink] = useState(true);

  const { x, alpha, combined } = useMemo(() => {
    const fs = 256;
    const secs = 6;
    const n = fs * secs;
    const xs: number[] = [];
    const a: number[] = [];
    const c: number[] = [];

    for (let i = 0; i < n; i++) {
      const t = i / fs;
      xs.push(t);
      // 10 Hz alpha with a slow amplitude wobble, which is how it really behaves.
      const env = 0.75 + 0.25 * Math.sin(2 * Math.PI * 0.28 * t);
      const av = alphaUv * env * Math.sin(2 * Math.PI * 10 * t);
      a.push(av);

      // Two blinks, shaped like the measured average: a fast peak then a
      // slower opposite rebound.
      let b = 0;
      for (const t0 of [1.9, 4.2]) {
        const dt = t - t0;
        b += blinkUv * Math.exp(-((dt / 0.11) ** 2));
        b -= blinkUv * 0.42 * Math.exp(-(((dt - 0.22) / 0.17) ** 2));
      }
      c.push(av + (showBlink ? b : 0));
    }
    return { x: xs, alpha: a, combined: c };
  }, [alphaUv, blinkUv, showBlink]);

  const ratio = blinkUv / Math.max(alphaUv, 1);
  const limit = Math.max(blinkUv * 1.15, alphaUv * 1.6);

  return (
    <>
      <LineChart
        series={[
          { label: 'What you wanted: 10 Hz alpha rhythm', color: 'var(--good)', x, y: alpha },
          ...(showBlink
            ? [{ label: 'What the electrode recorded', color: 'var(--worst)', x, y: combined }]
            : []),
        ]}
        xLabel="Seconds"
        yLabel="Microvolts"
        height={280}
        yMin={-limit}
        yMax={limit}
        caption="Both lines are drawn on the same scale. That is the whole point: the green line is the brain rhythm people build studies around, and the red line is what actually comes off the electrode when someone blinks twice."
      />

      <div className="grid two" style={{ marginTop: 6 }}>
        <div>
          <label htmlFor="alpha-slider">
            Alpha rhythm: <strong>{alphaUv} µV</strong>{' '}
            <span style={{ color: 'var(--ink-3)' }}>(10 to 50 is typical)</span>
          </label>
          <input
            id="alpha-slider"
            type="range"
            min={5}
            max={50}
            step={1}
            value={alphaUv}
            onChange={(e) => setAlphaUv(Number(e.target.value))}
          />
        </div>
        <div>
          <label htmlFor="blink-slider">
            Blink height: <strong>{blinkUv} µV</strong>{' '}
            <span style={{ color: 'var(--ink-3)' }}>(measured: 78 to 222)</span>
          </label>
          <input
            id="blink-slider"
            type="range"
            min={20}
            max={400}
            step={5}
            value={blinkUv}
            onChange={(e) => setBlinkUv(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="cta-row">
        <button className="btn ghost" onClick={() => setShowBlink((v) => !v)}>
          {showBlink ? 'Hide the blinks' : 'Add the blinks back'}
        </button>
      </div>

      <p className="note flag">
        At these settings the blink is <strong>{ratio.toFixed(1)} times</strong> the size of
        the rhythm underneath it. Average an epoch that contains one and the blink wins.
      </p>
    </>
  );
}

/** Real thirty second windows: resting, blinking, clenching. */
export function RealExamples() {
  const [items, setItems] = useState<Snippet[] | null>(null);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    fetch('/data/artifact-examples.json')
      .then((r) => r.json())
      .then((d) => setItems(d.items))
      .catch(() => setItems(null));
  }, []);

  if (!items?.length) return <p className="note">Loading the example recordings.</p>;

  const it = items[Math.min(idx, items.length - 1)];

  return (
    <>
      <div className="chips" style={{ marginBottom: 14 }}>
        {items.map((s, i) => (
          <button key={s.label} className="chip" aria-pressed={i === idx} onClick={() => setIdx(i)}>
            {s.label}
          </button>
        ))}
      </div>

      <TraceStrip
        channels={it.channels}
        durationS={it.duration_s}
        color={it.condition === 'BT' ? 'var(--worst)' : 'var(--accent)'}
      />

      <p style={{ fontSize: 15 }}>{it.note}</p>

      <div className="kv" style={{ marginTop: 4 }}>
        <span>
          <b>{it.peak_uv.toFixed(0)} µV</b>
          largest swing
        </span>
        <span>
          <b>{it.rms_uv.toFixed(1)} µV</b>
          typical size
        </span>
        <span>
          <b>{it.sfreq.toFixed(0)} Hz</b>
          sample rate
        </span>
        <span>
          <b>{it.duration_s.toFixed(0)} s</b>
          window
        </span>
      </div>

      <p style={{ fontSize: 13.5, color: 'var(--ink-3)', marginTop: 10 }}>
        Source file <code>{it.source}</code>, seconds {it.t0} to {it.t1}.
      </p>
    </>
  );
}
