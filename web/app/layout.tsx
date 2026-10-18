import type { Metadata } from 'next';
import localFont from 'next/font/local';
import { SiteFooter, SiteHeader } from '@/components/Shell';
import './globals.css';

// Erode, by Indian Type Foundry via Fontshare (ITF Free Font License), self-hosted at build
// time so the page makes no request to any font host.
const erode = localFont({
  variable: '--font-erode',
  display: 'swap',
  src: [
    { path: './fonts/Erode-Regular.woff2', weight: '400', style: 'normal' },
    { path: './fonts/Erode-Italic.woff2', weight: '400', style: 'italic' },
    { path: './fonts/Erode-Medium.woff2', weight: '500', style: 'normal' },
    { path: './fonts/Erode-Semibold.woff2', weight: '600', style: 'normal' },
  ],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://eeg-artifact-finder.vercel.app'),
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

// Applied before paint so a dark reader never sees a light flash. Marks JavaScript as working
// and carries the old storage key (eas-theme) over to the shared name once.
const THEME_SCRIPT =
  "(function(){var d=document.documentElement;d.classList.add('js');try{var t=localStorage.getItem('theme');" +
  "if(!t){var o=localStorage.getItem('eas-theme');if(o==='dark'||o==='light'){t=o;localStorage.setItem('theme',o);}" +
  "localStorage.removeItem('eas-theme');localStorage.removeItem('eas-notice-seen');}" +
  "if(t==='light'||t==='dark')d.setAttribute('data-theme',t);}catch(e){}})();";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={erode.variable} suppressHydrationWarning>
      <head>
        <meta name="color-scheme" content="light dark" />
        <meta name="theme-color" content="#f4f3ef" />
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <a className="skip" href="#main">Skip to main content</a>
        <SiteHeader />
        <main id="main">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
