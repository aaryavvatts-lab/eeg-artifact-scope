'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';

const NAV = [
  { href: '/check', label: 'Check a file' },
  { href: '/blink', label: 'What a blink does' },
  { href: '/devices', label: 'Headsets' },
  { href: '/findings', label: 'Findings' },
  { href: '/methods', label: 'Methods' },
  { href: '/data', label: 'Data' },
  { href: '/about', label: 'About' },
];

const THEME_KEY = 'eas-theme';
const NOTICE_KEY = 'eas-notice-seen';

function Wave() {
  return (
    <svg width="26" height="18" viewBox="0 0 26 18" fill="none" aria-hidden="true">
      <path
        d="M1 9h3.4l1.9-6.5L9.5 15l2.6-9 2.2 5.2L16.6 9H25"
        stroke="var(--accent)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function SiteHeader() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark' | null>(null);

  useEffect(() => {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === 'light' || saved === 'dark') {
      setTheme(saved);
      document.documentElement.setAttribute('data-theme', saved);
    }
  }, []);

  useEffect(() => setOpen(false), [path]);

  function toggle() {
    const current =
      theme ??
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem(THEME_KEY, next);
  }

  return (
    <header className="hdr">
      <div className="wrap hdr-in">
        <Link href="/" className="brand">
          <Wave />
          EEG Artifact Scope
        </Link>

        <nav className={`nav${open ? ' open' : ''}`} aria-label="Main">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              aria-current={path === n.href ? 'page' : undefined}
            >
              {n.label}
            </Link>
          ))}
        </nav>

        <button
          className="iconbtn menubtn"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={open ? 'Close menu' : 'Open menu'}
        >
          {open ? '✕' : '☰'}
        </button>

        <button
          className="iconbtn"
          onClick={toggle}
          aria-label="Switch between light and dark"
          title="Switch between light and dark"
        >
          {theme === 'dark' ? '☀' : '☽'}
        </button>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="ftr">
      <div className="wrap">
        <div className="ftr-grid">
          <div>
            <h4>The tool</h4>
            <ul>
              <li><Link href="/check">Check a file</Link></li>
              <li><Link href="/blink">What a blink does</Link></li>
              <li><Link href="/devices">Headset comparison</Link></li>
            </ul>
          </div>
          <div>
            <h4>The work</h4>
            <ul>
              <li><Link href="/findings">Findings</Link></li>
              <li><Link href="/methods">Methods</Link></li>
              <li><Link href="/data">Data sources</Link></li>
              <li><Link href="/about">About</Link></li>
            </ul>
          </div>
          <div>
            <h4>Legal</h4>
            <ul>
              <li><Link href="/privacy">Privacy</Link></li>
              <li><Link href="/terms">Terms of use</Link></li>
              <li><Link href="/cookies">Cookies and storage</Link></li>
              <li><Link href="/accessibility">Accessibility</Link></li>
            </ul>
          </div>
          <div>
            <h4>Code</h4>
            <ul>
              <li>
                <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope">
                  Source on GitHub
                </a>
              </li>
              <li>
                <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope/blob/main/SCORECARD.md">
                  Validation scorecard
                </a>
              </li>
            </ul>
          </div>
        </div>

        <p className="fine">
          This is a student research project, not a medical device. It is not approved
          by any regulator and must not be used to diagnose, treat, or make decisions
          about any person. Nothing you load here is uploaded. See the{' '}
          <Link href="/terms">terms of use</Link> before relying on any number it gives you.
        </p>
      </div>
    </footer>
  );
}

export function CookieNotice() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(NOTICE_KEY)) setShow(true);
  }, []);

  if (!show) return null;

  return (
    <div className="cookie" role="region" aria-label="Storage notice">
      <p>
        This site has no tracking or advertising cookies. It saves two things in your
        browser: whether you picked light or dark, and that you closed this box.{' '}
        <Link href="/cookies">What gets stored</Link>
      </p>
      <button
        className="btn"
        onClick={() => {
          localStorage.setItem(NOTICE_KEY, '1');
          setShow(false);
        }}
      >
        Got it
      </button>
    </div>
  );
}
