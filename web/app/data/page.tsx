import Link from 'next/link';

export const metadata = {
  title: 'Data sources',
  description:
    'The four public datasets this project used, who collected them, and the problems found in them.',
};

export default function DataPage() {
  return (
    <div className="wrap section prose">
      <p className="eyebrow">Four public datasets · none collected by me</p>
      <h1>Where the data came from</h1>
      <p className="lede">
        I did not record any of this. Four groups collected and published these datasets, and
        the whole project rests on their work. Their details are below, along with the problems
        I ran into, which are mine to report rather than theirs to answer for.
      </p>

      <h2>The main one: five headsets at once</h2>
      <p>
        Thirty people wore four consumer EEG devices and one research system at the same time
        while blinking, clenching their jaw, and moving their head on cue. Twenty repetitions
        per task, three seconds apart, with resting periods either side.
      </p>
      <p>
        Almost everything on this site depends on this dataset, because it is the only one where
        the ground truth is written down. Without it every threshold here would be a guess.
      </p>
      <ul>
        <li>
          Dataset: Ahn, M. and Lee, Y. (2026).{' '}
          <a href="https://doi.org/10.6084/m9.figshare.30162868">
            EEG dataset of consumer- and research-grade systems
          </a>
          . Figshare. Licensed CC BY 4.0.
        </li>
        <li>
          Paper: Lee, Y., Gwon, D., Kim, K. and colleagues (2026).{' '}
          <a href="https://doi.org/10.1038/s41598-026-39056-8">
            A comprehensive evaluation framework for consumer-grade EEG devices: signal quality,
            robustness, and usability
          </a>
          . Scientific Reports.
        </li>
        <li>Devices: BrainLink Pro, NeuroNicle FX2, MindWave Mobile 2, Muse 2, and a DSI-24.</li>
      </ul>

      <p className="note flag">
        <strong>Worth knowing before you read any of my numbers.</strong> The published dataset
        says a subset of noisy recordings was left out of the release. That is a reasonable
        decision for the authors&rsquo; own analysis, and it means my detector was tuned and
        checked on recordings that are already cleaner than average. Real world files will be
        worse than these. It is also why the Muse results rest on 26 people rather than 30.
      </p>

      <h2>Eye and heart electrodes: OpenNeuro ds002718</h2>
      <p>
        Eighteen people looking at pictures of faces, recorded with 70 EEG electrodes plus
        electrodes placed specifically to pick up eye movement and heartbeat. Those extra
        electrodes are the reason this dataset is here: they let me check blink detection that
        uses ordinary EEG channels against a recording that measured the eye directly.
      </p>
      <ul>
        <li>
          Original data: Wakeman, D. G. and Henson, R. N. (2015).{' '}
          <a href="https://doi.org/10.1038/sdata.2015.1">
            A multi-subject, multi-modal human neuroimaging dataset
          </a>
          . Scientific Data. Released CC0.
        </li>
        <li>
          The EEG portion, prepared for EEGLAB, is{' '}
          <a href="https://openneuro.org/datasets/ds002718">OpenNeuro ds002718</a>.
        </li>
      </ul>
      <p>
        One thing to watch if you use it. The EEGLAB file marks all 74 channels as EEG,
        including the two eye electrodes and the two heart electrodes. Trusting that label feeds
        an eye trace into your brain analysis. The companion channel table alongside the file
        has the correct types, and my reader uses it when it is present.
      </p>

      <h2>A clinical recording set</h2>
      <p>
        Forty people doing tasks at different difficulty levels, on a 32 channel clinical
        system. I planned to use its clean and noisy labels as an outside check on the quality
        score.
      </p>
      <ul>
        <li>
          <a href="https://figshare.com/articles/dataset/iNCog-EEG_ideal_vs_Noisy_Cognitive_EEG_for_Workload_Assessment_Dataset/30003127">
            iNCog-EEG
          </a>
          , Figshare, licensed CC BY 4.0.
        </li>
      </ul>
      <p>
        That check did not work. Across seven standard quality measures the labelled groups do
        not separate, and the numbers are in <Link href="/findings">findings</Link>. I am not
        saying the dataset is wrong, only that I could not reproduce the distinction its notes
        describe, so I did not use it as evidence.
      </p>
      <p>
        It earned its place anyway. It is what exposed the bandwidth bug, because it samples fast
        enough to look like it can show muscle activity while having been filtered so that it
        cannot.
      </p>

      <h2>A simulated set, mostly unreadable</h2>
      <p>
        Clean EEG with eye artifact added at known times, published alongside the original clean
        recording. That original would have allowed the strongest test in the project: not just
        whether an artifact is found, but how much real signal survives cleaning.
      </p>
      <ul>
        <li>
          <a href="https://data.mendeley.com/datasets/wb6yvr725d/1">
            A semi-simulated EEG/EOG dataset for the comparison of EOG artifact rejection
            techniques
          </a>
          , Mendeley Data, licensed CC BY 4.0.
        </li>
      </ul>
      <p>
        The archive as published is truncated. It lists 52,453,907 bytes of contents and is
        46,757,186 bytes, which matches the size the repository itself reports, so the download
        is complete and the hosted file is short. The clean recording fails its checksum with
        roughly 17 MB of the expected 23 MB present. Two unrelated extraction tools fail at the
        same point.
      </p>
      <p>
        The other two files opened fine, so a smaller version of the test was still possible. I
        have reported that instead, and said clearly what was lost.
      </p>

      <h2>Things the files hide</h2>
      <p>
        Every one of these cost time, and none is written in the documentation. If you work with
        these datasets, this list may save you an afternoon.
      </p>
      <ul>
        <li>
          <strong>Event times are in samples, not seconds.</strong> The notes say seconds. Read
          them as seconds and every event lands in the wrong place.
        </li>
        <li>
          <strong>The unit field is blank in the consumer device files.</strong> The format says
          it should not be. Read literally, the recordings claim the scalp produced 176 volts.
        </li>
        <li>
          <strong>Sixteen channels look like spare inputs but are not.</strong> They are named
          like unused sockets and carry real signal. Dropping them on the name alone throws away
          half the montage.
        </li>
        <li>
          <strong>Sampling rate is not bandwidth.</strong> One set samples at 200 Hz and holds
          nothing above about 38 Hz. Any measurement above that is noise.
        </li>
        <li>
          <strong>Sample rates and channel counts vary inside one dataset.</strong> Three
          different rates across the headsets, and the Muse gives four or six channels depending
          on the person.
        </li>
      </ul>

      <h2>Methods this project follows</h2>
      <ul>
        <li>
          Bigdely-Shamlo, N., Mullen, T., Kothe, C. and colleagues (2015).{' '}
          <a href="https://doi.org/10.3389/fninf.2015.00016">
            The PREP pipeline: standardized preprocessing for large-scale EEG analysis
          </a>
          . Frontiers in Neuroinformatics. The bad electrode checks come from here.
        </li>
        <li>
          Gramfort, A. and colleagues (2013).{' '}
          <a href="https://doi.org/10.3389/fnins.2013.00267">
            MEG and EEG data analysis with MNE-Python
          </a>
          . Frontiers in Neuroscience. Used offline as the reference my own readers are tested
          against, and as an independent second opinion on blink detection.
        </li>
        <li>
          Pernet, C., Appelhoff, S., Gorgolewski, K. J. and colleagues (2019).{' '}
          <a href="https://doi.org/10.1038/s41597-019-0104-8">
            EEG-BIDS, an extension to the brain imaging data structure for electroencephalography
          </a>
          . Scientific Data. The folder layout and channel tables follow this.
        </li>
        <li>
          The European Data Format specification, published at{' '}
          <a href="https://www.edfplus.info/specs/index.html">edfplus.info</a>. The reader in
          this project was written against it.
        </li>
      </ul>

      <h2>What is redistributed here</h2>
      <p>
        One file. The sample recording offered on the checking page is a single 56 second Muse 2
        window from the first dataset, kept so visitors can try the tool without owning an EEG
        recording. It is redistributed under CC BY 4.0 with attribution, and the notice sits
        beside it in the repository. No other data from any of these sets is hosted here.
      </p>

      <div className="cta-row">
        <Link className="btn" href="/findings">What the data showed</Link>
        <Link className="btn ghost" href="/methods">How it was analysed</Link>
      </div>
    </div>
  );
}
