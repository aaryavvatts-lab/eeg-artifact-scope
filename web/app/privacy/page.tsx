import Link from 'next/link';

export const metadata = {
  title: 'Privacy',
  description:
    'What this site collects, what it stores, and what happens to any EEG file you open with it.',
};

export const UPDATED = '29 August 2026';

export default function PrivacyPage() {
  return (
    <div className="wrap section prose narrow">
      <p className="eyebrow">Last updated {UPDATED}</p>
      <h1>Privacy</h1>

      <h2>The short version</h2>
      <p>
        There are no accounts, no sign in, no analytics and no advertising. Nothing you type or
        load is sent to a server. Two small values are saved in your own browser: whether you
        chose light or dark, and whether you closed the storage notice.
      </p>
      <p>
        The longer version below spells out what that means, because a claim like that is worth
        very little without the detail behind it.
      </p>

      <h2>Who runs this</h2>
      <p>
        EEG Artifact Scope is a personal research and education project by Aaryav Sharma. It is
        not run by a company, a university, a hospital or a laboratory. There is no organisation
        behind it and no commercial interest in it.
      </p>
      <p>
        The full source code is public at{' '}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope">
          github.com/aaryavvatts-lab/eeg-artifact-scope
        </a>
        . Anything described on this page can be checked there.
      </p>

      <h2>Your EEG recordings</h2>
      <p>This is the part that matters most, so it gets its own section.</p>
      <p>
        When you choose a file on the checking page, your browser reads it into memory in that
        tab. The analysis then runs inside the same tab, using a copy of the Python scientific
        libraries compiled to run in a browser. The file is <strong>not</strong> uploaded,{' '}
        <strong>not</strong> copied to a server, and <strong>not</strong> stored anywhere after
        you close or reload the page.
      </p>
      <p>There is no server that could receive it. The site is a set of static files.</p>
      <p>
        You do not have to take my word for this. Open your browser developer tools, go to the
        network tab, and run an analysis. You will see requests for the page, the maths
        libraries and the analysis package, and no request carrying your data anywhere.
      </p>
      <p>
        The same applies to results. Your score, the artifacts found and the channel names all
        stay in the tab and disappear when you leave.
      </p>

      <h2>What is stored on your device</h2>
      <p>
        Two values in your browser&rsquo;s local storage. No cookies are set by this site at all.
      </p>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>What it holds</th>
              <th>Why</th>
              <th>How long</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>eas-theme</code></td>
              <td><code>light</code> or <code>dark</code></td>
              <td>Keeps your appearance choice between visits</td>
              <td>Until you clear it</td>
            </tr>
            <tr>
              <td><code>eas-notice-seen</code></td>
              <td><code>1</code></td>
              <td>Stops the storage notice reappearing every visit</td>
              <td>Until you clear it</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p>
        Neither identifies you. Neither is sent anywhere. Both are removed if you clear site data
        in your browser settings, and the site works normally without them.
      </p>
      <p>
        More detail is on the <Link href="/cookies">cookies and storage page</Link>.
      </p>

      <h2>Hosting and server logs</h2>
      <p>
        The site is hosted by Vercel Inc. Like any web host, Vercel&rsquo;s servers process
        ordinary request information in order to deliver pages: IP address, the page requested,
        the time, your browser&rsquo;s user agent string, and similar technical detail. This
        happens for every website you visit and it is not something a static site can switch
        off.
      </p>
      <p>
        I have not enabled Vercel Analytics, Speed Insights, or any similar product. I do not
        have access to a dashboard of visitors, and I do not see who comes here or from where.
      </p>
      <p>
        Vercel&rsquo;s own privacy terms cover what they do with that infrastructure data, and
        are at{' '}
        <a href="https://vercel.com/legal/privacy-policy">vercel.com/legal/privacy-policy</a>.
      </p>

      <h2>Third parties</h2>
      <p>There are two, and both are narrow.</p>
      <p>
        <strong>Fonts.</strong> None. The typefaces are downloaded when the site is built and
        served from the same place as the site, so your browser never contacts a font host.
      </p>
      <p>
        <strong>The Python runtime.</strong> The analysis engine, Pyodide, is fetched from the
        jsDelivr content network the first time you run a check. That request tells jsDelivr your
        IP address and that you asked for those files, in the same way as loading any script from
        a content network. It carries none of your data, and it only happens on the checking
        page.
      </p>
      <p>
        There is no advertising, no tracking pixel, no social widget, no embedded video and no
        error reporting service.
      </p>

      <h2>Children</h2>
      <p>
        This site is aimed at researchers, students and clinicians. It is not directed at
        children, and since it collects no personal information at all, it does not knowingly
        collect anything from anyone of any age.
      </p>

      <h2>Your rights</h2>
      <p>
        Rules such as the UK and EU GDPR and the California Consumer Privacy Act give you rights
        over personal data an organisation holds about you: to see it, correct it, delete it, or
        object to its use.
      </p>
      <p>
        I hold none. There is no database, no mailing list and no account system, so there is
        nothing for me to show you, correct or erase. The two browser values described above are
        on your own device and only you can read or remove them.
      </p>
      <p>
        For the request data that reaches the host, contact Vercel using the policy linked above.
      </p>

      <h2>About the EEG recordings used to build this</h2>
      <p>
        The datasets behind the calibration were collected by other research groups and published
        openly under licences that permit reuse. Those studies obtained their own ethical
        approval and consent from their participants. I did not collect any recordings and I have
        no relationship with the people in them.
      </p>
      <p>
        Only one file is redistributed here: a 56 second sample recording so visitors can try the
        tool. Full details and credit are on the <Link href="/data">data page</Link>.
      </p>

      <h2>Changes</h2>
      <p>
        If this policy changes, the date at the top changes with it. The page is version
        controlled in the public repository, so the full history of what it said and when is
        visible there.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about this policy, or about anything on the site, can be raised as an issue on{' '}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope/issues">
          the project repository
        </a>
        .
      </p>
    </div>
  );
}
