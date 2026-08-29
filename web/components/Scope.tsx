'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { Analysis } from '@/lib/types';
import { Gauge, Spectrum, Timeline, Traces, scoreColor } from '@/components/Charts';
import { DeviceReportCard } from '@/components/DeviceReportCard';

const WHEEL_URL = './wheels/eeg_artifact_scope-0.1.0-py3-none-any.whl';
const SAMPLE_URL = './sample-muse2-blink.edf';

const STEPS = [
  ['runtime', 'Start the Python runtime'],
  ['packages', 'Load numpy and scipy'],
  ['install', 'Install the analysis package'],
  ['reading', 'Read your file'],
  ['analysing', 'Detect artifacts'],
] as const;

type Phase = 'idle' | 'working' | 'done' | 'error';

export default function Scope() {
  const workerRef = useRef<Worker | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [stage, setStage] = useState<string>('');
  const [detail, setDetail] = useState<string>('');
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<{ message: string; detail: string } | null>(null);
  const [over, setOver] = useState(false);
  const [filename, setFilename] = useState<string>('');

  useEffect(() => {
    const w = new Worker('./analysis-worker.js');
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

  const run = useCallback(async (buffer: ArrayBuffer, name: string) => {
    setPhase('working');
    setAnalysis(null);
    setError(null);
    setFilename(name);
    setStage('runtime');
    setDetail('Starting…');
    workerRef.current?.postMessage(
      { cmd: 'analyse', buffer, filename: name, wheelUrl: WHEEL_URL },
      [buffer],
    );
  }, []);

  const onFile = useCallback(
    async (file: File) => {
      run(await file.arrayBuffer(), file.name);
    },
    [run],
  );

  const loadSample = useCallback(async () => {
    const res = await fetch(SAMPLE_URL);
    run(await res.arrayBuffer(), 'sample-muse2-blink.edf');
  }, [run]);

  const busy = phase === 'working';
  const stepIndex = STEPS.findIndex(([k]) => k === stage);

  return (
    <main className="wrap">
      <header className="hero">
        <span className="badge">● Runs entirely in your browser</span>
        <h1>Is that brain activity, or your face?</h1>
        <p className="lead">
          Scalp EEG is measured in microvolts. A blink is measured in <strong>hundreds</strong> of
          them. One blink or jaw clench can be an order of magnitude larger than the neural
          signal underneath it — so it is genuinely hard to tell whether you recorded a brain
          or a facial muscle.
        </p>
        <p>
          Drop in a recording and find out what is actually in it: which artifacts, where they
          are, which channels to drop, and how much usable data you have left.
        </p>
      </header>

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
      >
        <h3>{busy ? 'Analysing…' : 'Drop an EEG file here'}</h3>
        <p>EDF · BDF · EEGLAB .set — or click to browse</p>
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
          <button
            className="btn ghost"
            onClick={(e) => {
              e.stopPropagation();
              loadSample();
            }}
          >
            or try a sample Muse 2 recording
          </button>
        )}
        {busy && (
          <ul className="steps">
            {STEPS.map(([key, label], i) => (
              <li
                key={key}
                className={i < stepIndex ? 'done' : i === stepIndex ? 'active' : ''}
              >
                {i < stepIndex ? '✓' : i === stepIndex ? '▸' : '·'} {label}
                {i === stepIndex && detail ? ` — ${detail}` : ''}
              </li>
            ))}
          </ul>
        )}
      </div>

      {phase === 'error' && error && (
        <div className="panel">
          <div className="err">
            <strong>Could not analyse {filename}.</strong>
            <p style={{ margin: '8px 0 0' }}>{error.message}</p>
          </div>
          <details style={{ marginTop: 12 }}>
            <summary style={{ cursor: 'pointer', fontSize: 13, color: 'var(--ink-faint)' }}>
              Technical detail
            </summary>
            <pre
              style={{
                fontSize: 11.5,
                overflowX: 'auto',
                color: 'var(--ink-faint)',
                marginTop: 8,
              }}
            >
              {error.detail}
            </pre>
          </details>
        </div>
      )}

      {phase === 'done' && analysis && <Report analysis={analysis} filename={filename} />}

      <footer>
        <p>
          Detection follows established EEG standards (PREP for bad channels, MNE&rsquo;s
          approach for ocular and muscle artifacts). Thresholds are calibrated against 30
          subjects performing <em>cued</em> blinks and jaw clenches, so they are measured
          rather than guessed — see{' '}
          <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope/blob/main/SCORECARD.md">
            the validation scorecard
          </a>
          , which reports the failures as well as the successes.
        </p>
        <p>
          Your recording is read into memory in this tab and never uploaded. There is no
          server to upload it to — this page is a static file.
        </p>
      </footer>
    </main>
  );
}

function Report({ analysis, filename }: { analysis: Analysis; filename: string }) {
  const q = analysis.quality;
  if (!q) return null;

  const f = analysis.file;
  const mins = (s: number) => (s >= 90 ? `${(s / 60).toFixed(1)} min` : `${s.toFixed(0)} s`);

  return (
    <>
      <section className="panel">
        <div className="scorerow">
          <Gauge score={q.score} grade={q.grade} />
          <div className="verdict">
            <p>{q.verdict}</p>
            <div className="stats">
              <span>
                <b>{mins(q.usable_seconds)}</b>
                usable of {mins(q.duration_s)}
              </span>
              <span>
                <b>{(q.usable_fraction * 100).toFixed(0)}%</b>
                survives rejection
              </span>
              <span>
                <b>
                  {q.n_channels - q.bad_channels.length}/{q.n_channels}
                </b>
                channels good
              </span>
              <span>
                <b>{f.sfreq.toFixed(0)} Hz</b>
                {f.format.toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        {q.bad_channels.length > 0 && (
          <div className="chips">
            {q.bad_channels.map((c) => (
              <span className="chip bad" key={c}>
                {c}
              </span>
            ))}
          </div>
        )}

        {q.warnings.map((w, i) => (
          <p className="note" key={i}>
            {w}
          </p>
        ))}
      </section>

      <section className="panel">
        <h2>What cost you points</h2>
        <p className="sub">
          The breakdown matters more than the number — a score with no provenance is not
          something you can act on.
        </p>
        {q.components.map((c) => (
          <div className={`comp${c.skipped ? ' skipped' : ''}`} key={c.kind}>
            <span className="name">{c.label}</span>
            <span className="bar">
              <i
                style={{
                  width: `${Math.min(100, (c.penalty / c.weight) * 100)}%`,
                  background: c.skipped ? 'var(--line)' : scoreColor(100 - (c.penalty / c.weight) * 100),
                }}
              />
            </span>
            <span className="num">{c.skipped ? 'n/a' : `−${c.penalty.toFixed(1)}`}</span>
            <span className="why">{c.explanation}</span>
          </div>
        ))}
        {q.skipped_checks.length > 0 && (
          <p className="note">
            Checks that could not run are shown as <em>n/a</em> rather than passing. A check
            that did not happen is not a clean result.
          </p>
        )}
      </section>

      <section className="panel">
        <h2>When the artifacts happened</h2>
        <p className="sub">One lane per artifact type. Darker means more severe.</p>
        <Timeline analysis={analysis} />
      </section>

      <DeviceReportCard analysis={analysis} />

      <section className="panel">
        <h2>The signal itself</h2>
        <p className="sub">{filename}</p>
        <Traces analysis={analysis} />
      </section>

      <section className="panel">
        <h2>Power spectrum</h2>
        <p className="sub">
          Averaged across channels. Mains hum shows as a spike at 50 or 60 Hz; a sharp
          roll-off means the recording was low-pass filtered.
        </p>
        <Spectrum analysis={analysis} />
      </section>
    </>
  );
}
