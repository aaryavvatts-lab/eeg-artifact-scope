import Link from 'next/link';

export const metadata = {
  title: 'Methods',
  description:
    'How each artifact is detected, how the thresholds were chosen, and the four mistakes that only showed up against real data.',
};

export default function MethodsPage() {
  return (
    <div className="wrap section prose">
      <p className="eyebrow">How it works</p>
      <h1>Methods</h1>
      <p className="lede">
        Nothing here is novel. The detectors follow methods that are already standard in EEG
        work. What took the time was finding out which of them quietly measure the wrong thing.
      </p>

      <h2>Before anything is measured</h2>
      <p>
        Files arrive in a state you cannot assume anything about, so the first step is to work
        out what is actually in them.
      </p>
      <ul>
        <li>
          Dead channels are dropped. A channel with no variation at all is an unplugged input,
          not a very calm brain.
        </li>
        <li>
          Electrode names are tidied up. Some systems label a channel by the pair it was measured
          across, like <code>Fp1-A1</code>, which matches no standard layout until the reference
          part is stripped off.
        </li>
        <li>
          Eye and heart channels are separated from brain channels, so they can be used as a
          reference rather than analysed as if they were EEG.
        </li>
        <li>
          Units are checked. One dataset leaves the unit field blank, which is against the format
          specification. Read literally it claims the scalp was producing 176 volts. The reader
          assumes microvolts, and records that it made that assumption.
        </li>
      </ul>
      <p className="note">
        A channel named like a spare input is <em>not</em> dropped automatically. One dataset has
        sixteen channels called <code>Add_lead1</code> through <code>Add_lead16</code> that carry
        real signal. Dropping them on the name alone quietly threw away half the montage, so now
        only genuinely dead channels go.
      </p>

      <h2>Blinks</h2>
      <p>
        Filter to 1 to 10 Hz, where blink energy sits. Use dedicated eye electrodes if the file
        has them, and otherwise build a stand in from whichever frontal electrodes exist, because
        the eye behaves like a small battery right behind the forehead. Then look for swings that
        stand out from that recording&rsquo;s own baseline.
      </p>
      <p>
        The baseline uses the median and the median absolute deviation rather than the mean and
        standard deviation. Artifacts are exactly the outliers being hunted, and a mean based
        measure lets them inflate their own baseline until they no longer look unusual.
      </p>
      <p>
        The part that needed fixing: a blink is not one swing. It rises, overshoots, and comes
        back, three peaks about 0.45 seconds apart. Picking peaks off the filtered signal counted
        each blink about three and a half times. Measuring the envelope instead turns the whole
        thing into one bump, and one blink counts once.
      </p>

      <h2>Muscle and jaw clenching</h2>
      <p>
        Muscle activity is fast and spread across frequencies, well above where brain rhythms
        have most of their power. So it shows up as a burst of high frequency energy, strongest
        near the temples.
      </p>
      <p>
        The textbook band is 110 to 140 Hz. Half the headsets here do not sample fast enough to
        see it. The obvious fix is to widen the band downwards, and that turns out to be wrong.
        Widening to 20 Hz destroyed the detector: it fired almost as often during blinking as
        during clenching, because real brain rhythms and blink energy live down there too.
      </p>
      <p>
        Taking the highest narrow window each recording can actually support works far better.
        On the same recordings that gives between three and thirty five times better separation
        between clenching and blinking, depending on how much bandwidth the hardware has.
      </p>
      <p className="note">
        A 50 or 60 Hz notch filter was tried here and dropped. It made the result slightly worse,
        because comparing against the recording&rsquo;s own baseline already cancels a constant
        hum, while the notch adds ringing of its own. Worth mentioning because it is the kind of
        step that gets added out of habit.
      </p>

      <h2>Broken electrodes</h2>
      <p>
        This follows the criteria from the PREP pipeline, which is the usual reference for this
        job. Four checks: no signal at all, an amplitude far out of step with the other
        electrodes, poor agreement with the rest of the head, and excess high frequency noise
        from bad contact.
      </p>
      <p>Two of those four were inverted when I first wrote them, and both looked correct.</p>
      <p>
        <strong>Agreement between electrodes.</strong> Artifacts hit every electrode at once, so
        they push agreement <em>up</em>. On a Muse, forehead electrodes agree at 0.41 while
        someone sits still and 0.88 while they blink hard. Flagging low agreement as broken
        marked three of four channels bad during quiet rest and none during heavy blinking. This
        check now only runs on caps with at least eight electrodes, since a four electrode
        headband has electrodes on opposite sides of the head that should not agree.
      </p>
      <p>
        <strong>High frequency noise.</strong> Measured as a share of total power, which sounds
        sensible until a large slow artifact inflates the total and makes a genuinely noisy
        electrode look clean. Now each electrode is compared against the others in the same
        recording instead of against a fixed number.
      </p>

      <h2>Mains hum, drift and electrode pops</h2>
      <p>
        Mains hum is a sharp peak at 50 or 60 Hz depending on the country. The tool works out
        which by looking at both and taking whichever is more prominent, then reports how far it
        stands above the surrounding spectrum. On the recordings here it correctly picks 60 Hz
        for the Korean dataset and 50 Hz for the British one.
      </p>
      <p>
        Drift is slow movement below 1 Hz: sweat, a settling electrode, a pulled cable. Pops are
        sudden steps from a contact breaking and remaking, so they are found on the difference
        between neighbouring samples rather than on the signal.
      </p>

      <h2>The mistake that ran through all of it</h2>
      <p>
        Everything above compares each moment against the rest of the same recording. That is the
        right way to find <em>where</em> something happened. It is useless for judging{' '}
        <em>how bad</em> a recording is, and it took a while to see why.
      </p>
      <p>
        Comparing a file against itself always flags a few percent of it. A pristine recording
        has a quietest part and a busiest part just like a ruined one. So every file scored about
        the same, and one very clean clinical recording came out with 48% drift and 76 electrode
        pops a minute on data whose slow movement never exceeds 12 microvolts.
      </p>
      <p>
        Events now have to clear two bars: unusual for this recording, and large enough in
        microvolts to matter. The absolute limits follow the range people already use when
        rejecting EEG segments by hand.
      </p>

      <h2>Turning that into a score</h2>
      <p>
        Each artifact type can remove a set number of points from 100. Muscle can take the most
        because it is the hardest to remove without losing real signal. Blinks take less because
        they have a consistent shape and standard cleaning handles them. Heartbeat takes very
        little because it is small and rarely a problem.
      </p>
      <p>
        Two rules keep the number honest. A check that could not run is reported as not assessed
        rather than passed, because a check that did not happen is not a clean result. And the
        head wide figure is a high percentile across electrodes rather than the worst one, since
        with seventy electrodes something is always the worst and taking it measures how many
        electrodes you own.
      </p>
      <p>
        The number people should actually read is minutes of usable data. That is the answer to
        the real question, which is whether there is enough left to analyse.
      </p>

      <h2>Why it runs in your browser</h2>
      <p>
        Two reasons, one practical and one that turned out to matter more.
      </p>
      <p>
        The practical one: the host this site runs on caps uploads at 4.5 MB and cuts off requests
        after a minute. EEG files here run from 50 MB to 234 MB. A normal upload and process
        design simply cannot work.
      </p>
      <p>
        The better reason: plenty of researchers work under ethics approvals that forbid sending
        recordings to a third party at all. A tool that requires an upload is not usable by them,
        whatever its privacy policy says. Running in the browser removes the question.
      </p>
      <p>
        The detection code has no dependency on MNE, which keeps it small enough to compile for
        the browser. MNE is still used offline as the reference the readers are checked against,
        and a test asserts the browser version produces the same samples from the same files.
      </p>

      <h2>Known limits</h2>
      <ul>
        <li>
          Thresholds come from healthy adults in a small number of labs. Clinical recordings from
          people with neurological conditions were not tested.
        </li>
        <li>
          Precision was never measured, because no dataset here has second by second video
          annotation of when people really blinked.
        </li>
        <li>
          Heartbeat detection without a dedicated heart electrode is marked low confidence, and
          it should be. It is inferred from regular rhythm, and other things are also regular.
        </li>
        <li>
          A 0.8 second gap is enforced between blinks, so genuine rapid blinking merges into one
          event. That barely affects contaminated time, which is what scoring uses, but it does
          understate the count.
        </li>
      </ul>

      <div className="cta-row">
        <Link className="btn" href="/findings">See the numbers</Link>
        <Link className="btn ghost" href="https://github.com/aaryavvatts-lab/eeg-artifact-scope">
          Read the code
        </Link>
      </div>
    </div>
  );
}
