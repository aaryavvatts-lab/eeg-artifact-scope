import Link from 'next/link';

export const metadata = {
  title: 'Terms of use',
  description:
    'What this tool is for, what it is not for, licensing, and the limits of what it can tell you.',
};

export default function TermsPage() {
  return (
    <div className="wrap section prose narrow">
      <p className="eyebrow">Last updated 29 August 2026</p>
      <h1>Terms of use</h1>

      <h2>The short version</h2>
      <p>
        This is a student research project. It is free to use and the code is open. It is not a
        medical device, it has not been reviewed by any regulator, and it must not be used to
        make decisions about anyone&rsquo;s health. It comes with no warranty and no guarantee
        that its numbers are correct for your data.
      </p>

      <h2>Not a medical device</h2>
      <p>This is the most important section on the page.</p>
      <p>
        EEG Artifact Scope is a signal quality tool. It looks at an electrical recording and
        estimates how much of it is contaminated by things that are not brain activity, such as
        blinking, muscle tension and electrode problems.
      </p>
      <p>It does not do any of the following, and cannot be made to:</p>
      <ul>
        <li>diagnose, screen for, or rule out any medical condition</li>
        <li>detect seizures, epileptic activity, or any other clinical finding</li>
        <li>assess brain health, cognitive ability, attention, emotion or mental state</li>
        <li>support or contribute to any decision about a person&rsquo;s treatment or care</li>
      </ul>
      <p>
        It has not been submitted to, cleared by, or approved by the FDA, the MHRA, the EMA, or
        any other regulator, and no claim of clinical validity is made for it. A quality score
        from this tool says something about a recording, never about the person the recording
        came from.
      </p>
      <p>
        If you are a clinician: treat it the way you would treat a script written by a colleague
        over a weekend. It can be a useful first look at whether a recording is worth analysing.
        It is not a second opinion, and it is not evidence.
      </p>

      <h2>What it is genuinely useful for</h2>
      <ul>
        <li>deciding whether a recording is clean enough to be worth analysing</li>
        <li>finding which electrodes to drop before you start</li>
        <li>getting a repeatable number to describe data quality in a methods section</li>
        <li>comparing recording setups against each other</li>
        <li>teaching people what artifacts look like and why they matter</li>
      </ul>
      <p>
        If you use it in academic work, please describe it as what it is, cite the version you
        used, and check its output against your own judgement before you rely on it.
      </p>

      <h2>No warranty</h2>
      <p>
        The software is provided as is, without warranty of any kind, express or implied,
        including but not limited to the warranties of merchantability, fitness for a particular
        purpose and non-infringement. In no event shall the author be liable for any claim,
        damages or other liability arising from the software or its use.
      </p>
      <p>
        In plainer words: the numbers may be wrong for your data. The thresholds were tuned on
        recordings from a small number of laboratories, mostly from healthy adults, on specific
        hardware. Your recordings may behave differently, and the tool has no way of knowing
        that. The known limits are set out in <Link href="/findings">findings</Link> and{' '}
        <Link href="/methods">methods</Link>, and they are not a formality.
      </p>

      <h2>Your data is your responsibility</h2>
      <p>
        Nothing you load is uploaded, so I never hold your recordings and never could. That also
        means the responsibility for them stays with you.
      </p>
      <p>
        If your recordings contain personal or health information about identifiable people, you
        remain responsible for handling them lawfully under whatever rules apply to you, whether
        that is an ethics approval, a data protection law, or an agreement with the people who
        gave the data. Running an analysis in your own browser does not change any of those
        obligations, though it does mean no third party ever receives the file.
      </p>

      <h2>Licence</h2>
      <p>
        The source code is released under the MIT licence, which lets you use, change and
        redistribute it, including commercially, as long as the copyright notice and licence text
        stay with it. The full text is in the{' '}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope">repository</a>.
      </p>
      <p>
        The written content of this site is available under Creative Commons Attribution 4.0.
        Use it and adapt it with credit.
      </p>
      <p>
        The datasets are not mine and keep their own licences, which are listed on the{' '}
        <Link href="/data">data page</Link>. If you use them, cite the groups who collected them
        rather than this site.
      </p>

      <h2>Availability</h2>
      <p>
        There is no guarantee that this site stays online, keeps working, or produces the same
        answer in future versions as it does today. If you need a stable version, clone the
        repository and pin a commit. The offline command line tool produces the same numbers as
        the website and does not depend on this site existing.
      </p>

      <h2>Acceptable use</h2>
      <p>Please do not:</p>
      <ul>
        <li>present its output as a clinical result or a medical opinion</li>
        <li>
          claim it has regulatory approval, clinical validation, or an accuracy it does not have
        </li>
        <li>
          resell it as a certified quality assurance product without doing the validation such a
          claim requires
        </li>
      </ul>
      <p>
        The first two are the ones that could hurt somebody. The tool is honest about what it
        does not know, and it should not be repackaged in a way that hides that.
      </p>

      <h2>Governing terms</h2>
      <p>
        This is a personal project with no company behind it. These terms are a plain statement
        of intent and limits rather than a commercial contract. Where local consumer law gives
        you rights that cannot be signed away, nothing here overrides them.
      </p>

      <h2>Contact</h2>
      <p>
        Questions, corrections and bug reports are welcome as issues on{' '}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope/issues">
          the project repository
        </a>
        . If you find a case where the tool is wrong, that is genuinely useful and I would like
        to know.
      </p>
    </div>
  );
}
