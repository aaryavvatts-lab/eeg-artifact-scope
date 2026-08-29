import Link from 'next/link';

export const metadata = {
  title: 'Cookies and storage',
  description: 'This site sets no cookies. It saves two settings in your browser, listed here in full.',
};

export default function CookiesPage() {
  return (
    <div className="wrap section prose narrow">
      <p className="eyebrow">Last updated 29 August 2026</p>
      <h1>Cookies and storage</h1>

      <h2>The short version</h2>
      <p>
        This site sets <strong>no cookies</strong>. Not one, of any kind, first party or third
        party. There is no consent banner asking you to accept tracking, because there is no
        tracking to accept.
      </p>
      <p>
        Two values are saved in your browser&rsquo;s local storage so the site behaves sensibly
        between visits. Both are listed below in full.
      </p>

      <h2>Everything that gets stored</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Key</th>
              <th>Type</th>
              <th>Value</th>
              <th>Purpose</th>
              <th>Expires</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>eas-theme</code></td>
              <td>Local storage</td>
              <td><code>light</code> or <code>dark</code></td>
              <td>Remembers whether you switched the appearance</td>
              <td>Never, until you clear it</td>
            </tr>
            <tr>
              <td><code>eas-notice-seen</code></td>
              <td>Local storage</td>
              <td><code>1</code></td>
              <td>Stops the storage notice showing on every visit</td>
              <td>Never, until you clear it</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2>Why there is no consent banner</h2>
      <p>
        Rules such as the EU ePrivacy Directive and the UK PECR require consent before storing
        information on someone&rsquo;s device, with an exception for storage that is strictly
        necessary for a service the user asked for.
      </p>
      <p>
        Both values above fall inside that exception. They exist only to honour a choice you
        made, they hold no identifier, they are never transmitted, and they cannot be used to
        recognise you here or anywhere else. Blocking them changes nothing except that the site
        forgets your appearance choice.
      </p>
      <p>
        The small notice at the bottom of the screen is there to tell you this, not to ask
        permission. Closing it is what sets the second value.
      </p>

      <h2>How to remove them</h2>
      <p>
        Clearing site data in your browser removes both immediately. In most browsers that is
        under settings, then privacy, then site data, searching for this site. Private browsing
        windows discard them when you close the window.
      </p>
      <p>
        You can also block local storage for this site entirely. Everything keeps working. You
        will get the appearance that matches your system setting, and the notice will reappear
        each visit.
      </p>

      <h2>What is deliberately absent</h2>
      <ul>
        <li>No analytics of any kind, including privacy-friendly ones</li>
        <li>No advertising or advertising identifiers</li>
        <li>No social media buttons or embeds</li>
        <li>No session recording or heatmaps</li>
        <li>No error reporting service</li>
        <li>No fingerprinting, and no attempt to recognise a returning visitor</li>
        <li>No third party fonts, since the typefaces are served from this site</li>
      </ul>

      <h2>Requests your browser does make</h2>
      <p>
        Storage is not the same as network activity, so for completeness, here is everything your
        browser fetches.
      </p>
      <ul>
        <li>
          <strong>This site.</strong> Pages, styles, fonts, the analysis package, and the small
          data files behind the charts. All from the same place as the site.
        </li>
        <li>
          <strong>jsDelivr, only on the checking page.</strong> The Python runtime that performs
          the analysis is fetched from a content delivery network the first time you run a check.
          That request tells jsDelivr your IP address and which files you asked for, the same as
          any script loaded from a network like it. None of your data goes with it.
        </li>
      </ul>
      <p>
        Your EEG file is never part of any request. That is covered in more detail on the{' '}
        <Link href="/privacy">privacy page</Link>.
      </p>
    </div>
  );
}
