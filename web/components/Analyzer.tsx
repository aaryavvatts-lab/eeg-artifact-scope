'use client';

import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Analysis, ArtifactEvent, DetectorOut } from '@/lib/types';
import { KIND_COLOR, LineChart, TraceStrip, scoreColor } from '@/components/Viz';

const WHEEL_URL = '/wheels/eeg_artifact_scope-0.1.0-py3-none-any.whl';
const SAMPLE_URL = '/sample-muse2-blink.edf';

const STEPS = [
  ['runtime', 'Start the Python runtime'],
  ['packages', 'Load the maths libraries'],
  ['install', 'Install the analysis code'],
  ['reading', 'Read your file'],
  ['analysing', 'Look for artifacts'],
] as const;

type Phase = 'idle' | 'working' | 'done' | 'error';

export default function Analyzer() {
  const workerRef = useRef<Worker | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [stage, setStage] = useState('');
  const [detail, setDetail] = useState('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<{ message: string; detail: string } | null>(null);
  const [over, setOver] = useState(false);
  const [filename, setFilename] = useState('');

  useEffect(() => {
    const w = new Worker('/analysis-worker.js');
    workerRef.current = w;
    w.onmessage = (e) => {
      const m = e.data;
      if (m.type === 'progress') {
        setStage(m.stage);
        setDetail(m.detail);
      } else if (m.type === 'result') {
        setAnalysis(m.payload as Analysis);
        setPhase('done');
      } else if (m.type === 'error') {
        setError({ message: m.message, detail: m.detail });
        setPhase('error');
      }
    };
    return () => w.terminate();
  }, []);

  const run = useCallback((buffer: ArrayBuffer, name: string) => {
    setPhase('working');
    setAnalysis(null);
    setError(null);
    setFilename(name);
    setStage('runtime');
    setDetail('Starting');
    workerRef.current?.postMessage(
      { cmd: 'analyse', buffer, filename: name, wheelUrl: WHEEL_URL },
      [buffer],
    );
  }, []);

  const onFile = useCallback(
    async (file: File) => run(await file.arrayBuffer(), file.name),
    [run],
  );

  const loadSample = useCallback(async () => {
    try {
      const res = await fetch(SAMPLE_URL);
      if (!res.ok) throw new Error(`sample unavailable (HTTP ${res.status})`);
      run(await res.arrayBuffer(), 'sample-muse2-blink.edf');
    } catch (err) {
      setPhase('error');
      setFilename('the sample recording');
      setError({
        message:
          'The sample would not load. You can still drop in your own EDF, BDF or EEGLAB file.',
        detail: String(err),
      });
    }
  }, [run]);

  const busy = phase === 'working';
  const stepIndex = STEPS.findIndex(([k]) => k === stage);

  return (
    <>
      <div
        className={`drop${over ? ' over' : ''}${busy ? ' busy' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f && !busy) onFile(f);
        }}
        onClick={() => {
          if (!busy) document.getElementById('file-input')?.click();
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !busy) {
            e.preventDefault();
            document.getElementById('file-input')?.click();
          }
        }}
        aria-label="Choose an EEG file to check"
      >
        <h3>{busy ? 'Working on it' : 'Drop an EEG file here'}</h3>
        <p>EDF, BDF or EEGLAB .set. Or click to browse.</p>
        <input
          id="file-input"
          type="file"
          accept=".edf,.bdf,.set"
          style={{ display: 'none' }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) onFile(f);
          }}
        />
        {!busy && (
          <div className="cta-row" style={{ justifyContent: 'center' }}>
            <button
              className="btn ghost"
              onClick={(e) => {
                e.stopPropagation();
                loadSample();
              }}
            >
              No file handy? Use a real Muse 2 recording
            </button>
          </div>
        )}
        {busy && (
          <ul className="steps">
            {STEPS.map(([key, label], i) => (
              <li key={key} className={i < stepIndex ? 'done' : i === stepIndex ? 'active' : ''}>
                {i < stepIndex ? '✓' : i === stepIndex ? '▸' : '·'} {label}
                {i === stepIndex && detail ? `, ${detail.toLowerCase()}` : ''}
              </li>
            ))}
          </ul>
        )}
      </div>

      {busy && (
        <p className="note">
          The first run takes about twenty seconds because your browser has to download the
          maths libraries. After that it is quick. Everything happens on your machine.
        </p>
      )}

      {phase === 'error' && error && (
        <div style={{ marginTop: 18 }}>
          <div className="err">
            <strong>Could not read {filename}.</strong>
            <p style={{ margin: '6px 0 0' }}>{error.message}</p>
          </div>
          <details style={{ marginTop: 10 }}>
            <summary style={{ cursor: 'pointer', fontSize: 13.5, color: 'var(--ink-3)' }}>
              Technical detail
            </summary>
            <pre style={{ fontSize: 11.5, overflowX: 'auto', color: 'var(--ink-3)' }}>
              {error.detail}
            </pre>
          </details>
        </div>
      )}

      {phase === 'done' && analysis && <Report analysis={analysis} filename={filename} />}
    </>
  );
}

function Report({ analysis, filename }: { analysis: Analysis; filename: string }) {
  const q = analysis.quality;
  if (!q) return null;

  const f = analysis.file;
  const dur = (s: number) => (s >= 90 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(0)} s`);

  return (
    <>
      <section className="section">
        <div className="card">
          <div className="scorerow">
            <Gauge score={q.score} grade={q.grade} />
            <div style={{ flex: 1, minWidth: 260 }}>
              <p style={{ fontSize: '1.05rem', marginBottom: 14 }}>{q.verdict}</p>
              <div className="kv">
                <span>
                  <b>{dur(q.usable_seconds)}</b>
                  usable of {dur(q.duration_s)}
                </span>
                <span>
                  <b>{(q.usable_fraction * 100).toFixed(0)}%</b>
                  survives rejection
                </span>
                <span>
                  <b>
                    {q.n_channels - q.bad_channels.length}/{q.n_channels}
                  </b>
                  electrodes usable
                </span>
                <span>
                  <b>{f.sfreq.toFixed(0)} Hz</b>
                  {f.format.toUpperCase()}
                </span>
              </div>
            </div>
          </div>

          {q.bad_channels.length > 0 && (
            <p className="note" style={{ marginBottom: 0 }}>
              Electrodes to drop before you analyse anything:{' '}
              <code>{q.bad_channels.join(', ')}</code>
            </p>
          )}

          {q.warnings.map((w, i) => (
            <p className="note flag" key={i} style={{ marginBottom: 0 }}>
              {w}
            </p>
          ))}
        </div>
      </section>

      <section className="section">
        <h2>What cost you points</h2>
        <p>
          The number on its own is not much use. This is where it came from, and how each
          part was measured.
        </p>
        <div className="card">
          {q.components.map((c) => (
            <div className={`comp${c.skipped ? ' skipped' : ''}`} key={c.kind}>
              <span style={{ fontSize: 14.5, color: c.skipped ? 'var(--ink-3)' : 'var(--ink)' }}>
                {c.label}
              </span>
              <span className="bar">
                <i
                  style={{
                    width: `${Math.min(100, (c.penalty / c.weight) * 100)}%`,
                    background: c.skipped
                      ? 'var(--line)'
                      : scoreColor(100 - (c.penalty / c.weight) * 100),
                  }}
                />
              </span>
              <span className="n">{c.skipped ? 'n/a' : `−${c.penalty.toFixed(1)}`}</span>
              <span className="why">{c.explanation}</span>
            </div>
          ))}
        </div>
        {q.skipped_checks.length > 0 && (
          <p className="note">
            Anything marked <em>n/a</em> could not be measured on this file, so it is left out
            rather than passed. A check that did not run is not a clean result.
          </p>
        )}
      </section>

      <section className="section">
        <h2>When each artifact happened</h2>
        <p>
          One row per kind of artifact. Darker blocks are stronger. If you are planning to cut
          bad segments out by hand, this is the map.
        </p>
        <Timeline analysis={analysis} />
      </section>

      {analysis.preview && (
        <section className="section">
          <h2>The recording itself</h2>
          <p style={{ color: 'var(--ink-3)', fontSize: 14.5 }}>{filename}</p>
          <TraceStrip
            channels={analysis.preview.channels as { name: string; minmax: [number, number][] }[]}
            durationS={analysis.preview.duration_s}
            caption={`Showing ${analysis.preview.n_shown} of ${analysis.preview.n_total} electrodes. Drawn as the highest and lowest value in each pixel column, so a brief spike does not vanish when the picture is shrunk.`}
          />
        </section>
      )}

      {analysis.psd && (
        <section className="section">
          <h2>Power spectrum</h2>
          <p>
            Averaged over electrodes. Mains hum shows up as a spike at 50 or 60 Hz. A cliff
            edge means the recording was filtered before you got it, and anything above that
            edge cannot be measured.
          </p>
          <LineChart
            series={[
              {
                label: 'Average across electrodes',
                color: 'var(--accent)',
                x: analysis.psd.freqs,
                y: analysis.psd.db,
              },
            ]}
            xLabel="Frequency (Hz)"
            yLabel="Power (dB)"
            markers={
              analysis.detectors?.line_noise?.detail?.line_frequency_hz
                ? [
                    {
                      x: analysis.detectors.line_noise.detail.line_frequency_hz as number,
                      label: `${analysis.detectors.line_noise.detail.line_frequency_hz} Hz mains`,
                      color: 'var(--worst)',
                    },
                  ]
                : []
            }
          />
        </section>
      )}

      <section className="section">
        <h2>What to do next</h2>
        <p>
          If the score is high, you are fine. If it is not, the useful question is which part
          of the breakdown is doing the damage.
        </p>
        <div className="grid three">
          <div className="card">
            <h3>Blinks</h3>
            <p style={{ fontSize: 15 }}>
              Annoying but fixable. They have a consistent shape, so component-based cleaning
              such as ICA usually pulls them out without taking much brain signal with them.
            </p>
          </div>
          <div className="card">
            <h3>Muscle</h3>
            <p style={{ fontSize: 15 }}>
              The worst of the three. It is spread across frequencies and sits on top of real
              beta and gamma activity, so cleaning it means losing some of what you wanted.
              Cutting those segments is often safer.
            </p>
          </div>
          <div className="card">
            <h3>Bad electrodes</h3>
            <p style={{ fontSize: 15 }}>
              Drop them and interpolate if you have a full cap. On a four electrode headband
              you do not have neighbours to interpolate from, so a dead electrode means a
              quarter of your data is gone.
            </p>
          </div>
        </div>
        <p style={{ marginTop: '1.4rem' }}>
          For the reasoning behind every threshold, see <Link href="/methods">methods</Link>.
          For how the numbers were checked, see <Link href="/findings">findings</Link>.
        </p>
      </section>
    </>
  );
}

function Gauge({ score, grade }: { score: number; grade: string }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * c;
  const color = scoreColor(score);
  return (
    <div className="gauge">
      <svg width="128" height="128" viewBox="0 0 128 128" aria-hidden="true">
        <circle cx="64" cy="64" r={r} fill="none" stroke="var(--panel-2)" strokeWidth="10" />
        <circle
          cx="64"
          cy="64"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${c - filled}`}
          transform="rotate(-90 64 64)"
        />
      </svg>
      <div className="val">
        <span className="num" style={{ color }}>{score.toFixed(0)}</span>
        <span className="grade">grade {grade}</span>
      </div>
      <span className="sr-only">Quality score {score.toFixed(0)} out of 100, grade {grade}.</span>
    </div>
  );
}

function Timeline({ analysis }: { analysis: Analysis }) {
  const duration = analysis.file.duration_s;
  const lanes: { kind: string; label: string; events: ArtifactEvent[] }[] = [];
  for (const d of Object.values(analysis.detectors) as DetectorOut[]) {
    if (d.skipped_reason || !d.events?.length) continue;
    lanes.push({ kind: d.kind, label: d.label, events: d.events });
  }

  if (!lanes.length) {
    return <p className="note">Nothing timed was detected in this recording.</p>;
  }

  const W = 1000;
  const laneH = 20;
  const gap = 7;
  const H = lanes.length * (laneH + gap);

  return (
    <figure>
      <div className="scroll">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ minWidth: 480, display: 'block' }}
             role="img" aria-label="Artifacts over time, one row per kind">
          {lanes.map((lane, i) => {
            const y = i * (laneH + gap);
            return (
              <g key={lane.kind}>
                <rect x="0" y={y} width={W} height={laneH} rx="4" fill="var(--panel-2)" />
                {lane.events.map((e, j) => (
                  <rect
                    key={j}
                    x={(e.onset / duration) * W}
                    y={y}
                    width={Math.max(1.5, (e.duration / duration) * W)}
                    height={laneH}
                    rx="2"
                    fill={KIND_COLOR[lane.kind] ?? 'var(--ink-3)'}
                    opacity={0.42 + 0.58 * e.severity}
                  >
                    <title>{`${lane.label} at ${e.onset.toFixed(1)} s, lasting ${e.duration.toFixed(2)} s`}</title>
                  </rect>
                ))}
                <text x="7" y={y + laneH - 6} fontSize="11" fill="var(--ink-2)"
                      fontFamily="var(--mono)"
                      style={{ paintOrder: 'stroke', stroke: 'var(--panel-2)', strokeWidth: 3 }}>
                  {lane.label}, {lane.events.length}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5,
                    color: 'var(--ink-3)', fontFamily: 'var(--mono)', marginTop: 4 }}>
        <span>0 s</span>
        <span>{duration.toFixed(0)} s</span>
      </div>
    </figure>
  );
}
