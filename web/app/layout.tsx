import type { Metadata } from 'next';
import { Atkinson_Hyperlegible, IBM_Plex_Mono, Newsreader } from 'next/font/google';
import { CookieNotice, SiteFooter, SiteHeader } from '@/components/Shell';
import './globals.css';

// Atkinson Hyperlegible was drawn by the Braille Institute to keep similar
// letters apart for low vision readers. Used for body text on purpose.
const body = Atkinson_Hyperlegible({
  subsets: ['latin'],
  weight: ['400', '700'],
  variable: '--font-body',
  display: 'swap',
});

const display = Newsreader({
  subsets: ['latin'],
  weight: ['400', '600'],
  variable: '--font-display',
  display: 'swap',
});

const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  metadataBase: new URL('https://eeg-artifact-scope.vercel.app'),
  title: {
    default: 'EEG Artifact Scope',
    template: '%s · EEG Artifact Scope',
  },
  description:
    'Check whether an EEG recording holds brain activity or blinks and jaw clenches. Runs in your browser, so the recording never leaves your machine.',
  openGraph: {
    title: 'EEG Artifact Scope',
    description:
      'Check whether an EEG recording holds brain activity or blinks and jaw clenches. Runs in your browser.',
    type: 'website',
  },
};

// Applied before paint so a dark reader never sees a white flash.
const THEME_SCRIPT = `try{var t=localStorage.getItem('eas-theme');if(t==='light'||t==='dark'){document.documentElement.setAttribute('data-theme',t)}}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${body.variable} ${display.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <a className="skip" href="#main">Skip to main content</a>
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
        <CookieNotice />
      </body>
    </html>
  );
}
