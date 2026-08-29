import Link from 'next/link';

export const metadata = {
  title: 'Accessibility',
  description:
    'What has been done to make this site usable with a keyboard, a screen reader, or reduced vision, and what still falls short.',
};

export default function AccessibilityPage() {
  return (
    <div className="wrap section prose narrow">
      <p className="eyebrow">Last updated 29 August 2026</p>
      <h1>Accessibility</h1>

      <p className="lede">
        This site aims to meet WCAG 2.1 level AA. Some of it does. This page says which parts,
        and is honest about the parts that do not, because a statement that only lists successes
        is not much use to anyone deciding whether they can use a site.
      </p>

      <h2>What has been done</h2>

      <h3>Reading</h3>
      <ul>
        <li>
          Body text is set in Atkinson Hyperlegible, a typeface drawn by the Braille Institute
          that pulls apart letters people commonly confuse, such as capital I, lowercase l and
          the digit 1.
        </li>
        <li>
          Text and background combinations were chosen to clear the 4.5 to 1 contrast ratio in
          both light and dark, and larger text clears 3 to 1.
        </li>
        <li>
          Line length is capped at around 68 characters, which keeps the eye from losing its
          place on the way back to the start of a line.
        </li>
        <li>Text resizes with the browser zoom and reflows down to 320 pixels wide.</li>
        <li>
          Light and dark both exist. The site follows your system setting until you override it.
        </li>
      </ul>

      <h3>Keyboard and screen readers</h3>
      <ul>
        <li>Every control can be reached and operated with a keyboard alone.</li>
        <li>
          A skip link is the first thing focused on each page, so you can jump past the
          navigation.
        </li>
        <li>
          Focus outlines are visible and were not removed, which is the single most common
          accessibility mistake on the web.
        </li>
        <li>
          Headings run in order without skipping levels, so screen reader users can navigate by
          structure.
        </li>
        <li>
          The file drop area is a real focusable control that responds to Enter and Space, not
          only to a mouse drag.
        </li>
        <li>Charts carry text descriptions, and toggle buttons report their pressed state.</li>
      </ul>

      <h3>Motion and layout</h3>
      <ul>
        <li>
          Nothing moves, flashes or animates on its own. Nothing on the site can trigger a
          seizure.
        </li>
        <li>
          Smooth scrolling and transitions switch off when your system asks for reduced motion.
        </li>
        <li>Wide tables and charts scroll inside their own box, so the page itself never does.</li>
      </ul>

      <h2>Where it still falls short</h2>
      <p>These are real gaps, not caveats.</p>
      <ul>
        <li>
          <strong>The charts are visual.</strong> Each has a text summary and a caption with the
          key numbers, and most sit next to a data table with the same figures. But the shape of
          a line is not fully conveyed in text, and reading a waveform by ear is not currently
          possible here.
        </li>
        <li>
          <strong>Colour carries meaning in the artifact timeline.</strong> Each row is labelled
          in text as well, so the information is not colour only, but the colours themselves are
          not distinguishable for every kind of colour blindness.
        </li>
        <li>
          <strong>The analysis takes about twenty seconds on first use</strong> and gives
          progress as a list of steps. A screen reader user gets that update only when they move
          focus back to it, since it is not announced automatically.
        </li>
        <li>
          <strong>No formal audit.</strong> Everything here was checked by hand and with browser
          tooling. It has not been tested by a professional auditor, nor with every screen reader.
        </li>
      </ul>

      <h2>Testing</h2>
      <p>
        Checked with keyboard only navigation, browser zoom to 200%, forced dark and light modes,
        a 320 pixel viewport, and reduced motion enabled. Contrast ratios were calculated rather
        than eyeballed.
      </p>

      <h2>If something does not work for you</h2>
      <p>
        Please tell me. Open an issue on{' '}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope/issues">the repository</a>{' '}
        describing what you were trying to do and what got in the way. Accessibility problems get
        priority over features.
      </p>
      <p>
        If the website itself is the barrier, the{' '}
        <Link href="/check">command line version</Link> produces the same analysis as plain text
        output, which works with any screen reader and needs no browser at all.
      </p>
    </div>
  );
}
