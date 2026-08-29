import Link from 'next/link';

export const metadata = {
  title: 'About',
  description: 'Who made this, why, and what it is honestly worth.',
};

export default function AboutPage() {
  return (
    <div className="wrap section prose narrow">
      <p className="eyebrow">About</p>
      <h1>About this project</h1>

      <p className="lede">
        EEG Artifact Scope is a personal research project by Aaryav Sharma. It started from a
        simple question and turned into a longer lesson about how easy it is to measure the
        wrong thing convincingly.
      </p>

      <h2>Where it started</h2>
      <p>
        The idea was straightforward. EEG recordings are full of things that are not brain
        activity. There are established ways to find those things. So build a tool that runs
        those methods and tells you how noisy a recording is.
      </p>
      <p>
        The detectors were the easy part. Nearly all of them are standard, and writing them took
        an afternoon each. Then I tested them against recordings where somebody had written down
        what actually happened, and most of them turned out to be measuring something other than
        what I thought.
      </p>
      <p>
        Five separate bugs, and not one of them was a crash or a wrong sign. Each was a
        reasonable looking measurement that answered a slightly different question from the one I
        was asking. A relative threshold that could not tell a clean file from a ruined one. A
        muscle band that was really measuring an empty filtered gap. A broken electrode check
        that rewarded contamination. A head wide statistic that mostly counted electrodes.
      </p>
      <p>
        Every one was caught by ground truth and none by reading the code. That is the part of
        this project I would keep if I had to throw away the rest.
      </p>

      <h2>What it is worth</h2>
      <p>
        Honestly: it is a well tested implementation of standard methods, checked against real
        recordings, with the failures written down. It is not new science. The detectors follow
        published work and the ideas are not mine.
      </p>
      <p>
        What is a little unusual is the calibration. Most artifact tools set their thresholds by
        judgement, because datasets where the artifacts are timestamped are rare. This one had
        access to thirty people blinking on cue while wearing five headsets at once, so the
        thresholds could be measured instead of chosen. That is worth something, and it is the
        reason the numbers on this site come with sample sizes attached.
      </p>
      <p>
        Two of my four planned tests failed outright. Both are written up in{' '}
        <Link href="/findings">findings</Link> rather than deleted, because a project that only
        reports what worked is not telling you enough to judge it.
      </p>

      <h2>Built with</h2>
      <p>
        The analysis is Python, using NumPy and SciPy, deliberately kept free of heavier
        dependencies so it can be compiled to run in a browser. MNE-Python is used offline as the
        reference that the browser readers are tested against, and as an independent second
        opinion on blink detection.
      </p>
      <p>
        The site is a static export with no backend at all. The analysis runs in a background
        thread in your tab through Pyodide, which is CPython compiled to WebAssembly. That is
        what makes it possible to check a 234 MB recording on a host that limits uploads to 4.5
        MB, and it is also why your file never leaves your machine.
      </p>
      <p>
        The code is at{' '}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope">
          github.com/aaryavvatts-lab/eeg-artifact-scope
        </a>{' '}
        under the MIT licence.
      </p>

      <h2>Thanks</h2>
      <p>
        To the groups who collected and published the datasets. None of this exists without them,
        and they are credited on the <Link href="/data">data page</Link>. Publishing a dataset
        openly is a lot of unglamorous work, and it is the only reason a project like this can be
        checked rather than merely asserted.
      </p>

      <h2>Still to do</h2>
      <ul>
        <li>
          Compare the rule based detectors against a trained model on the same cued labels. Set
          up, not yet run. It will be reported either way, including if the model loses.
        </li>
        <li>Test against clinical recordings, which have not been looked at at all.</li>
        <li>
          Find or build a dataset with second by second video annotation, which is the only way
          to get a real precision figure.
        </li>
        <li>Add a proper export, so a report can be attached to a methods section.</li>
      </ul>

      <div className="cta-row">
        <Link className="btn" href="/check">Try the tool</Link>
        <Link className="btn ghost" href="/findings">Read the findings</Link>
      </div>
    </div>
  );
}
