import Link from 'next/link';
import Analyzer from '@/components/Analyzer';

export const metadata = {
  title: 'Check a recording',
  description:
    'Drop an EEG file in and see which artifacts it holds, where they are, and how much usable data is left. Runs in your browser.',
};

export default function CheckPage() {
  return (
    <div className="wrap section">
      <p className="eyebrow">The tool</p>
      <h1>Check a recording</h1>
      <p className="lede">
        Drop in an EEG file. You will get back what was found, when it happened, which
        electrodes to drop, and how many minutes you can still use.
      </p>
      <p className="note">
        Nothing is uploaded. The analysis code runs inside this tab, so the file never leaves
        your machine. You can confirm that in your browser network tab while it works.
      </p>

      <Analyzer />

      <section className="section">
        <h2>What it reads</h2>
        <div className="scroll">
          <table>
            <caption>Formats the browser version can open on its own.</caption>
            <thead>
              <tr>
                <th>Format</th>
                <th>Extension</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>European Data Format</td>
                <td><code>.edf</code></td>
                <td>The usual export format. EDF+ annotations are read too.</td>
              </tr>
              <tr>
                <td>BioSemi</td>
                <td><code>.bdf</code></td>
                <td>Same layout, 24 bits per sample instead of 16.</td>
              </tr>
              <tr>
                <td>EEGLAB</td>
                <td><code>.set</code></td>
                <td>
                  Version 7 and earlier. If yours was saved as v7.3 it is an HDF5 file, which
                  the browser build cannot open. Re-save it from EEGLAB, or use the command
                  line tool.
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <h3>Formats that need the command line tool</h3>
        <p>
          MNE&rsquo;s own <code>.fif</code>, BrainVision, and whole BIDS folders are handled by
          the offline version, which can use MNE properly. It is the same detection code, so
          the numbers match.
        </p>
        <pre><code>{`git clone https://github.com/aaryavvatts-lab/eeg-artifact-scope
cd eeg-artifact-scope
uv venv --python 3.12
uv pip install -e ".[lab]"
uv run eeg-scope your-recording.fif -v`}</code></pre>
        <p>
          Point it at a folder instead of a file and it will check everything inside, then
          write a JSON report with <code>--json report.json</code>.
        </p>
      </section>

      <section className="section">
        <h2>Reading the result</h2>
        <p>
          The score runs from 0 to 100 and the grade follows the usual letters. It is a
          summary, not a verdict. The part that matters is the breakdown underneath it, since
          two recordings can score the same for completely different reasons and need
          completely different fixes.
        </p>
        <p>
          The other number to watch is minutes of usable data. A recording can score badly and
          still hold plenty of clean signal if the damage is bunched into a few stretches. It
          can also score reasonably and leave you short if the contamination is spread evenly.
        </p>
        <p>
          Thresholds were set against recordings where people blinked and clenched on cue, so
          they come from measurement rather than taste. The full working is in{' '}
          <Link href="/methods">methods</Link>, and the checks are in{' '}
          <Link href="/findings">findings</Link>.
        </p>
      </section>
    </div>
  );
}
