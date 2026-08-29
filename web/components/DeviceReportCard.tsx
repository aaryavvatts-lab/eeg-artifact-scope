'use client';

import { useEffect, useState } from 'react';
import type { Analysis } from '@/lib/types';

interface DeviceRow {
  label: string;
  tier: string;
  channels: number;
  blink_amplitude_uv: { mean: number | null; n: number };
  blink_to_background_ratio: { mean: number | null };
  jaw_usable_fraction: { mean: number | null };
  jaw_grade: string | null;
}

interface Benchmark {
  generated_at: string;
  device_report_card?: { devices: Record<string, DeviceRow>; caveat: string };
}

/**
 * Which measured device class does an uploaded file most resemble?
 *
 * Deliberately conservative, and honest when it is guessing: montage naming is
 * the only signal available from a bare file, so a match is reported as a
 * resemblance rather than as an identification.
 */
export function inferDeviceClass(a: Analysis): { key: string | null; why: string } {
  const names = (a.file.channel_names || []).map((n) => n.toLowerCase());
  const n = a.file.n_channels_analysed;

  const has = (x: string) => names.some((v) => v.includes(x));

  if (has('af7') && has('af8') && (has('tp9') || has('tp10'))) {
    return { key: 'Muse2', why: 'AF7/AF8/TP9/TP10 is the Muse 2 montage.' };
  }
  if (n === 1) {
    return {
      key: 'MW2',
      why: 'A single electrode, like the MindWave 2 and BrainLink Pro — both sit at Fp1, directly above the eye.',
    };
  }
  if (n >= 16) {
    return {
      key: 'DSI',
      why: `${n} channels puts this in research-grade territory, like the DSI-24.`,
    };
  }
  return {
    key: null,
    why: `${n} channels does not match any device in the benchmark, so no comparison is shown.`,
  };
}

export function DeviceReportCard({ analysis }: { analysis: Analysis }) {
  const [bench, setBench] = useState<Benchmark | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch('./benchmark.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then(setBench)
      .catch(() => setFailed(true));
  }, []);

  if (failed) return null;
  if (!bench?.device_report_card) return null;

  const devices = bench.device_report_card.devices;
  const match = inferDeviceClass(analysis);

  return (
    <section className="panel">
      <h2>Device Report Card</h2>
      <p className="sub">
        Thirty people performed the same cued blink and the same cued jaw clench while
        wearing five headsets <em>at the same time</em>. Same person, same instant,
        different hardware — so this measures the hardware, not the subject.
      </p>

      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Device</th>
              <th>Tier</th>
              <th className="num">Ch</th>
              <th className="num">Blink amplitude</th>
              <th className="num">vs background</th>
              <th className="num">Jaw minute usable</th>
              <th>Grade</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(devices).map(([key, d]) => (
              <tr key={key} className={key === match.key ? 'you' : undefined}>
                <td>{d.label}</td>
                <td style={{ color: 'var(--ink-faint)' }}>{d.tier}</td>
                <td className="num">{d.channels}</td>
                <td className="num">
                  {d.blink_amplitude_uv.mean == null
                    ? '—'
                    : `${d.blink_amplitude_uv.mean.toFixed(0)} µV`}
                </td>
                <td className="num">
                  {d.blink_to_background_ratio.mean == null
                    ? '—'
                    : `${d.blink_to_background_ratio.mean.toFixed(1)}×`}
                </td>
                <td className="num">
                  {d.jaw_usable_fraction.mean == null
                    ? '—'
                    : `${(d.jaw_usable_fraction.mean * 100).toFixed(0)}%`}
                </td>
                <td>{d.jaw_grade ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="note">
        <strong>Your file:</strong> {match.why}
      </p>

      <p className="note">
        A blink is 10–23× the size of the background EEG on every device tested, which is
        the whole problem: it is not a small contaminant, it is the largest thing in the
        recording. Note the research-grade DSI-24 does <em>not</em> come out ahead on jaw
        survivability — more electrodes cover more head, and it captures the artifact more
        faithfully.
      </p>

      <p className="note">{bench.device_report_card.caveat}</p>
    </section>
  );
}
