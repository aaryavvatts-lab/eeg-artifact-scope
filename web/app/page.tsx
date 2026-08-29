import Link from 'next/link';

export const metadata = {
  title: 'EEG Artifact Scope: is that brain activity, or your face?',
  description:
    'A browser tool that checks whether an EEG recording holds brain activity or blinks and jaw clenches. Calibrated on 30 people wearing five headsets at once.',
};

const TOOLS = [
  {
    n: '01',
    href: '/check',
    title: 'Check your own file',
    tag: 'EDF, BDF, EEGLAB',
    body:
      'Drop in a recording. You get every artifact it found, where each one sits in time, which electrodes to throw away, and how many minutes of clean data you have left.',
  },
  {
    n: '02',
    href: '/blink',
    title: 'See what a blink does',
    tag: '1,477 real blinks',
    body:
      'The average blink from four headsets, drawn from real recordings. Slide the alpha rhythm up and down and watch how easily one blink buries it.',
  },
  {
    n: '03',
    href: '/devices',
    title: 'Compare headsets',
    tag: 'Same person, same second',
    body:
      'Thirty people wore five headsets at once and blinked on cue. This is how each one held up, and where your own file sits against them.',
  },
  {
    n: '04',
    href: '/findings',
    title: 'Read the numbers',
    tag: 'Including two failures',
    body:
      'Every result, with the controls that produced it. Two of the four things I set out to test did not work, and both are written up here.',
  },
];

export default function Home() {
  return (
    <>
      <section className="wrap section" style={{ paddingTop: '3rem' }}>
        <p className="eyebrow">30 people · 5 headsets at once · 20 cued blinks each · open data</p>
        <h1 style={{ maxWidth: '16ch' }}>Is that brain activity, or your face?</h1>
        <p className="lede">
          Brain waves at the scalp are a few millionths of a volt. A blink is a few hundred.
          So the thing most likely to show up in your EEG recording is not a brain at all. It
          is an eyelid, or a jaw, or a wire moving against skin.
        </p>
        <p className="lede">
          This tool reads a recording and tells you which of those it found, when they
          happened, and how much of your data survives. It runs inside your browser, so the
          file stays on your machine.
        </p>
        <div className="cta-row">
          <Link className="btn" href="/check">Check a recording</Link>
          <Link className="btn ghost" href="/blink">See what a blink does</Link>
        </div>
      </section>

      <section className="wrap">
        <div className="stats">
          <div className="stat">
            <b>88 to 100%</b>
            <span>of cued blinks found, depending on the headset</span>
          </div>
          <div className="stat">
            <b>30 of 30</b>
            <span>people whose jaw clench scored worse than their own rest minute</span>
          </div>
          <div className="stat">
            <b>4.2×</b>
            <span>how far an average blink stands above the ordinary signal</span>
          </div>
          <div className="stat">
            <b>0 bytes</b>
            <span>of your recording sent anywhere</span>
          </div>
        </div>
      </section>

      <section className="wrap section">
        <h2>Why this is worth building</h2>
        <p>
          If you record EEG, you already know the problem. You get a file back, you see
          wiggles, and you cannot always tell whether the wiggles came from the brain or from
          the face wrapped around it. Blinks, swallows, clenched teeth, a cable brushing a
          shoulder. All of them are bigger than the signal you wanted.
        </p>
        <p>
          Most people check this by eye. That works if you are experienced and the file is
          short. It stops working when you have forty recordings and a deadline, and it never
          gives you a number you can put in a methods section.
        </p>
        <p>
          What I wanted was something that gives an honest answer to one question: how much of
          this recording can I actually use? Not a quality grade with no reasoning behind it,
          but a list of what was found, when, and what it cost you.
        </p>

        <h2>Where the calibration comes from</h2>
        <p>
          Any tool like this needs to be checked against recordings where somebody wrote down
          what really happened. Otherwise you are just trusting the author.
        </p>
        <p>
          There is a dataset that does exactly that. Thirty people sat with{' '}
          <strong>five EEG headsets on their head at the same time</strong>, from a hundred
          pound headband up to a research system, and blinked or clenched their jaw every time
          they heard a beep. Twenty beeps, three seconds apart, with the beep times saved in
          the file.
        </p>
        <p>
          That means the same blink, from the same person, at the same instant, was recorded
          five different ways. So I can ask whether the detector found it, and separately, how
          badly each piece of hardware suffered. Both answers come from measurement rather
          than opinion.
        </p>

        <h2>Four things that went wrong</h2>
        <p>
          These are worth reading before you trust anything else on this site, because each
          one looked completely fine in the code and only fell apart against real data.
        </p>

        <div className="grid two" style={{ marginTop: '1.2rem' }}>
          <div className="card">
            <span className="tag bad">Wrong for weeks</span>
            <h3>Every recording scored about the same</h3>
            <p>
              I was measuring how unusual each moment was compared to the rest of the same
              file. That always flags a few percent of anything, however clean it is. A
              pristine recording and a ruined one came out nearly identical.
            </p>
          </div>
          <div className="card">
            <span className="tag bad">Silent</span>
            <h3>A filter got read as muscle tension</h3>
            <p>
              One dataset samples fast enough to see muscle activity but throws that band away
              before saving. The tool measured the empty band, found electrical noise, and
              reported 17% muscle contamination on every channel of every subject.
            </p>
          </div>
          <div className="card">
            <span className="tag bad">Backwards</span>
            <h3>Two checks rewarded bad data</h3>
            <p>
              Artifacts hit every electrode at once, which makes channels agree with each
              other more, not less. So the check for a broken electrode was calling channels
              broken during quiet rest and healthy during heavy blinking.
            </p>
          </div>
          <div className="card">
            <span className="tag bad">Unfair</span>
            <h3>More electrodes looked like more noise</h3>
            <p>
              With 70 electrodes, one of them is always the worst. Taking the worst meant a
              good research cap scored below a cheap headband recorded on the same head at the
              same moment. That was counting electrodes, not noise.
            </p>
          </div>
        </div>

        <p className="note flag">
          All four are fixed, and the fix for each is written up in{' '}
          <Link href="/methods">methods</Link>. I am listing them here because a tool that
          claims to measure data quality should be honest about the quality of its own
          measuring.
        </p>
      </section>

      <section className="wrap section">
        <h2>Four things you can do here</h2>
        <p style={{ color: 'var(--ink-3)', fontSize: 15 }}>
          Everything runs on real recordings. Nothing you load is sent anywhere.
        </p>

        <div className="grid two" style={{ marginTop: '1.2rem' }}>
          {TOOLS.map((t) => (
            <Link key={t.href} href={t.href} className="card link">
              <span className="num">{t.n}</span>
              <h3 style={{ marginTop: 4 }}>{t.title}</h3>
              <p style={{ fontSize: 15 }}>{t.body}</p>
              <span className="tag">{t.tag}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="wrap section">
        <h2>Two things worth saying plainly</h2>

        <h3>This is not a medical device</h3>
        <p>
          It is a student research project. No regulator has looked at it. It cannot tell you
          anything about a person&rsquo;s health, and it must not be used to make a decision
          about anybody&rsquo;s care. If you are a clinician, treat it the way you would treat
          a script a colleague wrote: useful for a first look, never the last word.
        </p>

        <h3>Your recording stays with you</h3>
        <p>
          There is no upload and no account. The analysis code is compiled to run in your
          browser, so the file is read into the tab and nothing leaves. That is partly a
          privacy decision and partly a practical one, since plenty of researchers work under
          ethics approvals that forbid sending recordings to a third party at all. You can
          check this yourself in the network tab.
        </p>

        <div className="cta-row">
          <Link className="btn" href="/check">Try it on a recording</Link>
          <Link className="btn ghost" href="/data">Where the data came from</Link>
        </div>
      </section>
    </>
  );
}
