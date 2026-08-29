import Link from 'next/link';
import { DeviceCompare, ThresholdSweep } from '@/components/DeviceLab';

export const metadata = {
  title: 'How headsets compare',
  description:
    'Thirty people wore five EEG headsets at the same time and blinked on cue. This is how each one handled it.',
};

export default function DevicesPage() {
  return (
    <div className="wrap section">
      <p className="eyebrow">Same person · same second · five headsets</p>
      <h1>How the hardware holds up</h1>
      <p className="lede">
        Comparing EEG headsets is normally guesswork, because two people wearing two headsets
        are two different experiments. This dataset avoids that by putting five headsets on
        one head at the same time.
      </p>

      <section className="section">
        <h2>What was recorded</h2>
        <p>
          Thirty people wore a research system and several consumer headsets together. On each
          beep they blinked, or clenched their jaw, or turned their head. Twenty beeps, three
          seconds apart, with a resting minute before and after.
        </p>
        <p>
          Because every headset heard the same beep on the same head, any difference between
          them is the hardware. Not the person, not the day, not how tired they were.
        </p>

        <div className="grid three" style={{ marginTop: '1.2rem' }}>
          <div className="card">
            <span className="tag">Research grade</span>
            <h3>DSI-24</h3>
            <p style={{ fontSize: 15 }}>
              Twenty four dry electrodes in a full cap. No gel, which makes it quick to fit
              and noisier at rest than a wet system would be.
            </p>
          </div>
          <div className="card">
            <span className="tag">Consumer</span>
            <h3>Muse 2</h3>
            <p style={{ fontSize: 15 }}>
              Four electrodes in a headband. Two behind the ears, two on the forehead directly
              above the eyes, which is the worst possible place to be during a blink.
            </p>
          </div>
          <div className="card">
            <span className="tag">Consumer</span>
            <h3>MindWave 2 and BrainLink Pro</h3>
            <p style={{ fontSize: 15 }}>
              One electrode each, sitting on the forehead. With a single channel there is
              nothing to cross-check against, so a bad contact is invisible.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <h2>The comparison</h2>
        <p>
          Pick a measure. Every bar comes from the recordings described above, and the table
          underneath gives the same numbers with how many recordings sit behind each one.
        </p>
        <DeviceCompare />
      </section>

      <section className="section">
        <h2>The result I did not expect</h2>
        <p>
          The research headset does not win. On the measure that matters most, how far a blink
          stands above the ordinary signal, the cheap headbands are worse, but not by the
          margin the price difference suggests. And the research cap records the largest blink
          of all four in absolute terms.
        </p>
        <p>
          Some of that is placement. The Muse sits its forehead electrodes right over the
          eyebrows, so a blink lands square on them. Some of it is that the research system
          uses dry electrodes, which are convenient but noisier at rest than gel.
        </p>
        <p className="note flag">
          There is a version of this comparison that is unfair, and I published the unfair one
          first. The head wide measure used to be the worst electrode on the head. With twenty
          four electrodes one of them is always the worst, so the research cap looked dirty
          next to a four electrode headband recorded on the same head at the same moment. That
          was counting electrodes, not noise. Switching to a high percentile fixed it, and the
          research cap moved from a C to a B.
        </p>
      </section>

      <section className="section">
        <h2>How the threshold was chosen</h2>
        <p>
          A detector needs a cut off, and picking one by eye is how you end up with a tool that
          works on your own files and nobody else&rsquo;s. Because the beep times are known,
          the cut off can be measured instead.
        </p>
        <p>
          The two lines below pull in opposite directions. Set the threshold too high and real
          blinks are missed. Set it too low and one blink gets counted several times, which
          quietly inflates every rate the tool reports.
        </p>
        <ThresholdSweep />
        <p>
          The shipped setting is the one that keeps both acceptable across all four headsets
          at once, which is a stricter requirement than tuning each device separately.
        </p>
      </section>

      <section className="section">
        <h2>What this does and does not tell you</h2>
        <p>
          It tells you how these four headsets behaved on thirty people in one laboratory on
          one day, with these electrodes in these positions. That is a real result and it is
          more than most comparisons offer.
        </p>
        <p>
          It does not tell you that one brand is better than another in general. Electrode
          placement, skin preparation, and how tight the band is all matter, and none of them
          were varied here. A Muse fitted carefully will beat a research cap fitted badly.
        </p>
        <div className="cta-row">
          <Link className="btn" href="/check">See where your file sits</Link>
          <Link className="btn ghost" href="/findings">Read the rest of the numbers</Link>
        </div>
      </section>
    </div>
  );
}
