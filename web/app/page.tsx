import Link from 'next/link';
import Reveal from '@/components/Reveal';

export const metadata = {
  title: 'EEG Artifact Scope: is that brain activity, or your face?',
  description:
    'A browser tool that checks whether an EEG recording holds brain activity or blinks and jaw clenches. Calibrated on 30 people wearing five headsets at once.',
};

/* The page is the object: an EEG recording strip. The first screen holds a real strip of the
   project's own data, and every later section is another piece of the same paperwork. All the
   numbers are the ones the scorecard reports. */
const TOOLS = [
  { href: '/check', title: 'Check your own file', tag: 'EDF, BDF, EEGLAB',
    body: 'Drop in a recording. You get every artifact it found, where each one sits in time, which electrodes to throw away, and how many minutes of clean data you have left.' },
  { href: '/blink', title: 'See what a blink does', tag: '1,477 real blinks',
    body: 'The average blink from four headsets, drawn from real recordings. Slide the alpha rhythm up and down and watch how easily one blink buries it.' },
  { href: '/devices', title: 'Compare headsets', tag: 'Same person, same second',
    body: 'Thirty people wore five headsets at once and blinked on cue. This is how each one held up, and where your own file sits against them.' },
  { href: '/findings', title: 'Read the numbers', tag: 'Including two failures',
    body: 'Every result, with the controls that produced it. Two of the four things I set out to test did not work, and both are written up here.' },
];

function Pair({ stem, alt, w, h }: { stem: string; alt: string; w: number; h: number }) {
  return (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="only-light" src={`/pictures/${stem}-light.png`} alt={alt} width={w} height={h} loading="lazy" decoding="async" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="only-dark" src={`/pictures/${stem}-dark.png`} alt={alt} width={w} height={h} loading="lazy" decoding="async" />
    </>
  );
}

export default function Home() {
  return (
    <>
      <section className="wrap hero" aria-label="Introduction">
        <div>
          <h1 className="lines">
            <span className="line"><span data-line style={{ ['--i' as string]: 0 }}>Brain activity,</span></span>
            <span className="line"><span data-line style={{ ['--i' as string]: 1 }}>or your face?</span></span>
          </h1>
          <p className="lede" data-rise style={{ ['--i' as string]: 2 }}>
            Brain waves at the scalp are a few millionths of a volt. A blink is a few hundred.
            So the thing most likely to show up in your EEG recording is not a brain at all. It
            is an eyelid, or a jaw, or a wire moving against skin.
          </p>
          <p data-rise style={{ ['--i' as string]: 3 }}>
            This tool reads a recording and tells you which of those it found, when they
            happened, and how much of your data survives. It runs inside your browser, so the
            file stays on your machine.
          </p>
          <div className="cta-row" data-rise style={{ ['--i' as string]: 4 }}>
            <Link className="btn" href="/check">Check a recording</Link>
            <Link className="textbtn" href="/blink">See what a blink does</Link>
          </div>
        </div>
        <div className="strip">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="only-light" src="/pictures/artifacts-light.png" alt="Six real EEG excerpts from the same person and headset: rest, blinking and jaw clenching, each three channels" width={1400} height={1040} fetchPriority="high" />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="only-dark" src="/pictures/artifacts-dark.png" alt="Six real EEG excerpts from the same person and headset: rest, blinking and jaw clenching, each three channels" width={1400} height={1040} fetchPriority="high" />
          <p className="cap">
            Six thirty-second excerpts from the study, same person, same headset, drawn as the
            envelope of each channel. Rest first, then cued blinks and jaw clenches.
          </p>
        </div>
      </section>

      <Reveal as="div" className="wrap facts" aria-label="Key figures">
        <div><b>88 to 100%</b><span>of cued blinks found, depending on the headset</span></div>
        <div><b>30 of 30</b><span>people whose jaw clench scored worse than their own rest minute</span></div>
        <div><b>4.2&times;</b><span>how far an average blink stands above the ordinary signal</span></div>
        <div><b>0 bytes</b><span>of your recording sent anywhere</span></div>
      </Reveal>

      <Reveal className="wrap section">
        <div className="narrow">
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
        </div>
      </Reveal>

      <Reveal className="plate" aria-labelledby="calib">
        <div>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/pictures/eeg-cap-nasa.jpg" alt="An astronaut wearing an EEG electrode cap aboard the International Space Station" width={1920} height={1080} loading="lazy" decoding="async" />
          <p className="small" style={{ marginTop: '.6rem' }}>An electrode cap in use. NASA photograph, not one of the thirty people in the study.</p>
        </div>
        <div>
          <h2 id="calib">Checked against thirty people</h2>
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
        </div>
      </Reveal>

      <Reveal className="wrap section pair" aria-label="Two figures from the calibration">
        <figure>
          <Pair stem="blinks" alt="The average blink shape from four headsets, with its spread, drawn from 1,477 real blinks" w={1200} h={1500} />
          <figcaption>The average blink on each of four headsets, with its spread. 1,477 real blinks. The shape is the same; the size is not.</figcaption>
        </figure>
        <figure>
          <Pair stem="sweep" alt="Share of cued blinks found at each detection threshold, one line per headset, with the shipped setting marked" w={1200} h={700} />
          <figcaption>How many cued blinks the detector finds as its threshold moves, per headset. The dashed line is the setting that ships.</figcaption>
        </figure>
      </Reveal>

      <section className="wrap section" id="wrong">
        <h2>Four things that went wrong</h2>
        <p className="narrow">
          These are worth reading before you trust anything else on this site, because each
          one looked completely fine in the code and only fell apart against real data.
        </p>
        <div className="wrong" style={{ marginTop: '2rem' }}>
          <Reveal as="article" index={0}>
            <h3>Every recording scored about the same</h3>
            <div>
              <p>
                I was measuring how unusual each moment was compared to the rest of the same
                file. That always flags a few percent of anything, however clean it is. A
                pristine recording and a ruined one came out nearly identical.
              </p>
              <p className="verdict">Wrong for weeks.</p>
            </div>
          </Reveal>
          <Reveal as="article" index={1}>
            <h3>A filter got read as muscle tension</h3>
            <div>
              <p>
                One dataset samples fast enough to see muscle activity but throws that band away
                before saving. The tool measured the empty band, found electrical noise, and
                reported 17% muscle contamination on every channel of every subject.
              </p>
              <p className="verdict">Silent.</p>
            </div>
          </Reveal>
          <Reveal as="article" index={2}>
            <h3>Two checks rewarded bad data</h3>
            <div>
              <p>
                Artifacts hit every electrode at once, which makes channels agree with each
                other more, not less. So the check for a broken electrode was calling channels
                broken during quiet rest and healthy during heavy blinking.
              </p>
              <p className="verdict">Backwards.</p>
            </div>
          </Reveal>
          <Reveal as="article" index={3}>
            <h3>More electrodes looked like more noise</h3>
            <div>
              <p>
                With 70 electrodes, one of them is always the worst. Taking the worst meant a
                good research cap scored below a cheap headband recorded on the same head at the
                same moment. That was counting electrodes, not noise.
              </p>
              <p className="verdict">Unfair.</p>
            </div>
          </Reveal>
        </div>
        <p className="note flag" style={{ marginTop: '2rem' }}>
          All four are fixed, and the fix for each is written up in{' '}
          <Link href="/methods">methods</Link>. I am listing them here because a tool that
          claims to measure data quality should be honest about the quality of its own
          measuring.
        </p>
      </section>

      <Reveal className="plate" aria-labelledby="filtered">
        <div>
          <h2 id="filtered">The filter that looked like muscle</h2>
          <p>
            Three systems, each spectrum normalised to its own level at 10 Hz. A sharp drop
            means the system filtered that band away, so anything measured above it is noise
            rather than physiology. The clinical system stops at 37.5 Hz. That is the empty
            band the tool once read as 17% muscle contamination.
          </p>
          <p><Link href="/methods">How the fix works</Link></p>
        </div>
        <div>
          <Pair stem="spectra" alt="Average spectrum of three EEG systems, each dropping sharply at its own filter edge" w={1200} h={700} />
        </div>
      </Reveal>

      <Reveal className="wrap section" id="tools">
        <h2>Four things you can do here</h2>
        <p className="narrow">Everything runs on real recordings. Nothing you load is sent anywhere.</p>
        <div className="toolrows" style={{ marginTop: '2rem' }}>
          {TOOLS.map((t, i) => (
            <Reveal as="div" key={t.href} index={i}>
              <Link href={t.href}>
                <span className="name">{t.title}</span>
                <span className="desc">{t.body}</span>
                <span className="tag">{t.tag}</span>
              </Link>
            </Reveal>
          ))}
        </div>
      </Reveal>

      <Reveal className="wrap section">
        <div className="narrow">
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
            <Link className="textbtn" href="/data">Where the data came from</Link>
          </div>
        </div>
      </Reveal>
    </>
  );
}
