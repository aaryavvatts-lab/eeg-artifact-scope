import Link from 'next/link';
import { BlinkShape, BuriedAlpha, RealExamples } from '@/components/BlinkLab';

export const metadata = {
  title: 'What a blink does to EEG',
  description:
    'The average blink measured from 1,477 real recordings on four headsets, and what it does to the brain rhythm underneath it.',
};

export default function BlinkPage() {
  return (
    <div className="wrap section">
      <p className="eyebrow">1,477 real blinks · 4 headsets · 30 people</p>
      <h1>What a blink actually does</h1>
      <p className="lede">
        Everyone who works with EEG is told that blinks are a problem. Fewer people have seen
        the size of one drawn next to the signal it lands on. This page does that, using real
        blinks rather than a drawing of a blink.
      </p>

      <section className="section">
        <h2>The average blink, measured</h2>
        <p>
          Thirty people blinked on cue while wearing several headsets at once. Every blink the
          detector found was cut out, lined up, and averaged. Pick a headset and you get the
          shape that hardware actually recorded.
        </p>
        <p>
          The shape is not a simple bump. It rises fast, overshoots, and comes back the other
          way. That matters more than it sounds: my first detector counted each of those
          three swings as a separate blink and reported three and a half times too many.
        </p>
        <BlinkShape />
      </section>

      <section className="section">
        <h2>Why it ruins the signal</h2>
        <p>
          Alpha is the rhythm you see when someone closes their eyes and relaxes. It sits
          around 10 Hz and runs somewhere between 10 and 50 microvolts. It is one of the most
          studied signals in the field.
        </p>
        <p>
          Drag the sliders and watch what one blink does to it. Both lines share a vertical
          scale, which is the only honest way to draw this.
        </p>
        <BuriedAlpha />
        <p>
          This is why a quality check is not fussiness. If a blink lands in your epoch, the
          average you compute afterwards is partly a description of an eyelid.
        </p>
      </section>

      <section className="section">
        <h2>Thirty seconds of the real thing</h2>
        <p>
          These are unedited windows from the recordings, same person and same headset, so you
          can compare rest against blinking against clenching without anything else changing.
        </p>
        <RealExamples />
        <p className="note">
          Notice the difference between the blink windows and the jaw window. Blinks are big,
          slow and regular, which makes them easy to spot and fairly easy to remove. Jaw
          muscle is fast and messy and sits on top of the frequencies people care about, which
          makes it much harder to get rid of without losing real signal.
        </p>
      </section>

      <section className="section">
        <h2>How the detector finds them</h2>
        <p>
          Blinks are biggest at the front of the head because the eye is a small battery
          sitting right behind the forehead electrodes. So the first step is to build a signal
          from whichever frontal electrodes exist, filter it to the 1 to 10 Hz range where
          blink energy lives, and look for swings that stand out from that recording&rsquo;s
          own baseline.
        </p>
        <p>
          Two details took a while to get right. The first is that the three swings of one
          blink have to be treated as one event, which means measuring the envelope of the
          signal rather than the signal itself. The second is that most headsets have no
          dedicated eye electrode at all, so the detector has to work from ordinary EEG
          channels. That case was checked against recordings that <em>do</em> have proper eye
          electrodes, and the two agree about 78% of the time.
        </p>
        <p>
          The full reasoning, including the thresholds and how they were picked, is in{' '}
          <Link href="/methods">methods</Link>.
        </p>
        <div className="cta-row">
          <Link className="btn" href="/check">Check your own recording</Link>
          <Link className="btn ghost" href="/devices">See how headsets compare</Link>
        </div>
      </section>
    </div>
  );
}
