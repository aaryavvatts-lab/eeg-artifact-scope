'use client';

import { useEffect, useMemo, useState } from 'react';

export interface SampleSource {
  name: string;
  authors: string;
  url: string;
  licence: string;
  file: string;
  window_s: [number, number];
}

export interface SampleEntry {
  slug: string;
  title: string;
  group: string;
  device: string;
  about: string;
  look_for: string;
  file: string;
  bytes: number;
  seconds: number;
  channels: number;
  channels_analysed: number;
  sfreq: number;
  source: SampleSource;
  expected: {
    score: number;
    grade: string;
    dominant: string | null;
    usable_fraction: number;
    bad_channels: number;
    skipped: number;
  };
}

const kb = (b: number) => (b >= 1024 * 1024 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.round(b / 1024)} KB`);

export function SamplePicker({
  onPick,
  busy,
}: {
  onPick: (buffer: ArrayBuffer, name: string, sample: SampleEntry) => void;
  busy: boolean;
}) {
  const [samples, setSamples] = useState<SampleEntry[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [slug, setSlug] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('/samples/manifest.json')
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => {
        setSamples(d.samples);
        if (d.samples?.length) setSlug(d.samples[0].slug);
      })
      .catch(() => setFailed(true));
  }, []);

  const groups = useMemo(() => {
    const out: Record<string, SampleEntry[]> = {};
    for (const s of samples ?? []) (out[s.group] ??= []).push(s);
    return out;
  }, [samples]);

  const chosen = samples?.find((s) => s.slug === slug);

  async function run() {
    if (!chosen || busy || loading) return;
    setLoading(true);
    try {
      const res = await fetch(chosen.file);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onPick(await res.arrayBuffer(), `${chosen.slug}.edf`, chosen);
    } catch {
      setFailed(true);
    } finally {
      setLoading(false);
    }
  }

  if (failed) {
    return (
      <div className="card">
        <h3>Example recordings unavailable</h3>
        <p style={{ marginBottom: 0 }}>
          The example files did not load. You can still check your own EDF, BDF or EEGLAB
          file using the box above.
        </p>
      </div>
    );
  }

  if (!samples) {
    return (
      <div className="card">
        <p style={{ marginBottom: 0, color: 'var(--ink-3)' }}>Loading example recordings.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>No EEG file? Try a real one</h3>
      <p style={{ fontSize: 15 }}>
        Ten excerpts from published studies, picked so they behave differently from each
        other. Some are clean, some are ruined, and two of them show the tool refusing to
        answer rather than guessing.
      </p>

      <div className="picker">
        <label htmlFor="sample-select">Choose a recording</label>
        <select
          id="sample-select"
          value={slug}
          onChange={(e) => setSlug(e.target.value)}
          disabled={busy || loading}
        >
          {Object.entries(groups).map(([group, list]) => (
            <optgroup key={group} label={group}>
              {list.map((s) => (
                <option key={s.slug} value={s.slug}>
                  {s.title} ({s.device.split(',')[0]})
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>

      {chosen && (
        <div className="sample-detail">
          <div className="sample-meta">
            <span>{chosen.device}</span>
            <span>{chosen.seconds.toFixed(0)} s</span>
            <span>
              {chosen.channels_analysed === chosen.channels
                ? `${chosen.channels} channels`
                : `${chosen.channels_analysed} EEG of ${chosen.channels} channels`}
            </span>
            <span>{kb(chosen.bytes)}</span>
          </div>

          <p style={{ fontSize: 15 }}>{chosen.about}</p>

          <p style={{ fontSize: 15 }}>
            <strong>What to look for:</strong> {chosen.look_for}
          </p>

          <div className="cta-row" style={{ marginTop: 12 }}>
            <button className="btn" onClick={run} disabled={busy || loading}>
              {loading ? 'Fetching' : busy ? 'Working' : 'Run this recording'}
            </button>
            <a className="btn ghost" href={chosen.file} download>
              Download the file
            </a>
          </div>

          <p className="sample-source">
            Excerpt of <code>{chosen.source.file}</code>, seconds {chosen.source.window_s[0]} to{' '}
            {chosen.source.window_s[1]}, from{' '}
            <a href={chosen.source.url}>{chosen.source.name}</a> by {chosen.source.authors},{' '}
            {chosen.source.licence}. Cropped and rewritten as EDF for this site.
          </p>
        </div>
      )}
    </div>
  );
}

/** Shown after a sample finishes, so the visitor can tell if it did the right thing. */
export function SampleCheck({ sample, score }: { sample: SampleEntry; score: number }) {
  const diff = Math.abs(score - sample.expected.score);
  const matches = diff < 0.6;

  return (
    <p className={`note${matches ? '' : ' flag'}`}>
      {matches ? (
        <>
          This example is expected to score{' '}
          <strong>
            {sample.expected.score.toFixed(1)} ({sample.expected.grade})
          </strong>
          , and it did. That figure was produced by running the same analysis on this exact
          file before the site was built, so if your browser disagreed with it, something
          would be wrong.
        </>
      ) : (
        <>
          Heads up: this example was expected to score{' '}
          <strong>{sample.expected.score.toFixed(1)}</strong> and scored{' '}
          <strong>{score.toFixed(1)}</strong> here. That gap should not happen, and it is
          worth reporting as a bug.
        </>
      )}
    </p>
  );
}

/** All ten examples at a glance, with the score each is known to produce. */
export function SampleTable() {
  const [samples, setSamples] = useState<SampleEntry[] | null>(null);

  useEffect(() => {
    fetch('/samples/manifest.json')
      .then((r) => r.json())
      .then((d) => setSamples(d.samples))
      .catch(() => setSamples(null));
  }, []);

  if (!samples) return <p className="note">Loading the list.</p>;

  return (
    <div className="scroll">
      <table>
        <thead>
          <tr>
            <th>Recording</th>
            <th>Hardware</th>
            <th className="num">Electrodes</th>
            <th className="num">Length</th>
            <th className="num">Score</th>
            <th>Mostly costs it</th>
          </tr>
        </thead>
        <tbody>
          {samples.map((s) => (
            <tr key={s.slug}>
              <td>{s.title}</td>
              <td style={{ color: 'var(--ink-3)' }}>{s.device.split(',')[0]}</td>
              <td className="num">{s.channels_analysed}</td>
              <td className="num">{s.seconds.toFixed(0)} s</td>
              <td className="num">
                {s.expected.score.toFixed(1)} ({s.expected.grade})
              </td>
              <td style={{ fontSize: 14 }}>
                {s.expected.skipped > 0 ? 'a check it refuses to run' : s.expected.dominant ?? 'nothing much'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
