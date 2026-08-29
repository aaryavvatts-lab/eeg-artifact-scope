'use client';

import { useEffect, useState } from 'react';
import { BarChart, LineChart } from '@/components/Viz';

interface Summary { mean: number | null; n: number; ci95?: [number, number] | null }

interface DeviceRow {
  label: string;
  tier: string;
  channels: number;
  blink_amplitude_uv: Summary;
  blink_to_background_ratio: Summary;
  jaw_usable_fraction: Summary;
  blink_score_cost: Summary;
  jaw_score_cost: Summary;
  jaw_grade: string | null;
}

interface Benchmark {
  generated_at: string;
  device_report_card?: { devices: Record<string, DeviceRow>; caveat: string };
}

const COLORS = ['var(--accent)', 'var(--highlight)', 'var(--good)', 'var(--warn)'];

const METRICS = [
  {
    key: 'blink_amplitude_uv' as const,
    label: 'How big a blink lands',
    unit: ' µV',
    help:
      'The size of the swing a blink puts into the electrodes, in microvolts. Bigger is worse, but it also reflects how faithfully the hardware records what is really there.',
  },
  {
    key: 'blink_to_background_ratio' as const,
    label: 'Blink against ordinary signal',
    unit: '×',
    help:
      'The full top to bottom swing of individual blinks, divided by how much the signal normally varies at rest. This runs higher than the figure on the blink page, which averages many blinks together and measures height rather than full swing. Both are honest, they answer slightly different questions.',
  },
  {
    key: 'jaw_usable_fraction' as const,
    label: 'Data left after a jaw clench',
    unit: '',
    help:
      'The share of a clenching minute that still counts as usable. Higher is better.',
  },
  {
    key: 'jaw_score_cost' as const,
    label: 'Points lost to clenching',
    unit: ' pts',
    help:
      'How far the quality score drops between a person resting and the same person clenching, on the same headset in the same recording.',
  },
];

export function DeviceCompare() {
  const [bench, setBench] = useState<Benchmark | null>(null);
  const [metric, setMetric] = useState(1);

  useEffect(() => {
    fetch('/benchmark.json')
      .then((r) => r.json())
      .then(setBench)
      .catch(() => setBench(null));
  }, []);

  const card = bench?.device_report_card;
  if (!card) return <p className="note">Loading the measured comparison.</p>;

  const m = METRICS[metric];
  const entries = Object.entries(card.devices);

  const items = entries
    .map(([key, d], i) => {
      const s = d[m.key];
      let v = s?.mean ?? 0;
      if (m.key === 'jaw_usable_fraction') v = v * 100;
      return {
        label: `${d.label} (${d.channels} ch)`,
        value: Number(v.toFixed(m.key === 'blink_to_background_ratio' ? 1 : 0)),
        color: COLORS[i % COLORS.length],
        note: s?.n ? `${s.n} recordings` : undefined,
      };
    })
    .sort((a, b) => b.value - a.value);

  return (
    <>
      <div className="chips" style={{ marginBottom: 16 }}>
        {METRICS.map((x, i) => (
          <button key={x.key} className="chip" aria-pressed={i === metric} onClick={() => setMetric(i)}>
            {x.label}
          </button>
        ))}
      </div>

      <BarChart
        items={items}
        unit={m.key === 'jaw_usable_fraction' ? '%' : m.unit}
        caption={m.help}
      />

      <div className="scroll" style={{ marginTop: '1.6rem' }}>
        <table>
          <caption>
            Everything measured, with the number of recordings behind each figure.
          </caption>
          <thead>
            <tr>
              <th>Headset</th>
              <th>Class</th>
              <th className="num">Electrodes</th>
              <th className="num">Blink size</th>
              <th className="num">Against background</th>
              <th className="num">Usable after clenching</th>
              <th>Grade</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([key, d]) => (
              <tr key={key}>
                <td>{d.label}</td>
                <td style={{ color: 'var(--ink-3)' }}>{d.tier}</td>
                <td className="num">{d.channels}</td>
                <td className="num">
                  {d.blink_amplitude_uv.mean == null ? 'not measured' : `${d.blink_amplitude_uv.mean.toFixed(0)} µV`}
                </td>
                <td className="num">
                  {d.blink_to_background_ratio.mean == null
                    ? 'not measured'
                    : `${d.blink_to_background_ratio.mean.toFixed(1)}×`}
                </td>
                <td className="num">
                  {d.jaw_usable_fraction.mean == null
                    ? 'not measured'
                    : `${(d.jaw_usable_fraction.mean * 100).toFixed(0)}%`}
                </td>
                <td>{d.jaw_grade ?? 'not measured'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="note">{card.caveat}</p>
    </>
  );
}

interface Sweep {
  thresholds: number[];
  shipped_default: number;
  note: string;
  devices: Record<string, { label: string; n_files: number; recall: number[]; detections_per_cue: number[]; rest_per_minute: number[] }>;
}

/** The calibration curve that set the shipped threshold. */
export function ThresholdSweep() {
  const [data, setData] = useState<Sweep | null>(null);
  const [dev, setDev] = useState('MW2');

  useEffect(() => {
    fetch('/data/threshold-sweep.json')
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data) return <p className="note">Loading the calibration curve.</p>;

  const keys = Object.keys(data.devices);
  const d = data.devices[dev] ?? data.devices[keys[0]];
  if (!d) return null;

  return (
    <>
      <div className="chips" style={{ marginBottom: 14 }}>
        {keys.map((k) => (
          <button key={k} className="chip" aria-pressed={k === dev} onClick={() => setDev(k)}>
            {data.devices[k].label}
          </button>
        ))}
      </div>

      <LineChart
        series={[
          {
            label: 'Share of cued blinks found',
            color: 'var(--good)',
            x: data.thresholds,
            y: d.recall,
          },
          {
            label: 'Detections per cued blink (1.0 is the target)',
            color: 'var(--accent)',
            x: data.thresholds,
            y: d.detections_per_cue,
          },
        ]}
        xLabel="Detection threshold"
        yLabel="Rate"
        height={270}
        markers={[
          { x: data.shipped_default, label: 'shipped setting', color: 'var(--highlight)' },
        ]}
        caption={`Measured on ${d.n_files} recordings from the ${d.label}. Raising the threshold misses real blinks. Lowering it splits one blink into several. The shipped setting sits where both stay acceptable across all four headsets, not just this one.`}
      />

      <LineChart
        series={[
          {
            label: 'False detections while sitting still',
            color: 'var(--worst)',
            x: data.thresholds,
            y: d.rest_per_minute,
          },
        ]}
        xLabel="Detection threshold"
        yLabel="Per minute"
        height={210}
        markers={[
          { x: data.shipped_default, label: 'shipped setting', color: 'var(--highlight)' },
        ]}
        caption="Detections per minute during the rest periods, when people were told to sit still. Not all of these are mistakes: people blink on their own roughly 10 to 20 times a minute, so a low number here is expected rather than perfect."
      />
    </>
  );
}

interface BandwidthItem {
  label: string;
  note: string;
  sfreq: number;
  effective_bandwidth_hz: number;
  freqs: number[];
  db: number[];
}

/** Sample rate against usable bandwidth. */
export function BandwidthDemo() {
  const [data, setData] = useState<{ items: BandwidthItem[] } | null>(null);

  useEffect(() => {
    fetch('/data/bandwidth.json')
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData(null));
  }, []);

  if (!data?.items?.length) return <p className="note">Loading the spectra.</p>;

  const colors = ['var(--worst)', 'var(--accent)', 'var(--good)'];

  return (
    <>
      <LineChart
        series={data.items.map((it, i) => ({
          label: it.label,
          color: colors[i % colors.length],
          x: it.freqs,
          y: it.db,
        }))}
        xLabel="Frequency (Hz)"
        yLabel="Power, dB below the level at 10 Hz"
        height={300}
        caption="Each recording is shown against its own level at 10 Hz, so the three can be compared despite different hardware. A line that falls off a cliff has been filtered, and nothing above that cliff can be measured."
      />

      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Recording</th>
              <th className="num">Sample rate</th>
              <th className="num">Actually usable to</th>
              <th>What that means</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => (
              <tr key={it.label}>
                <td>{it.label}</td>
                <td className="num">{it.sfreq.toFixed(0)} Hz</td>
                <td className="num">{it.effective_bandwidth_hz.toFixed(0)} Hz</td>
                <td style={{ fontSize: 14 }}>{it.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
