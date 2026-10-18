'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import ThemeToggle from '@/components/ThemeToggle';

const TOOLS = [
  { href: '/check', label: 'Check a file' },
  { href: '/blink', label: 'What a blink does' },
  { href: '/devices', label: 'Headsets' },
];
const READ = [
  { href: '/findings', label: 'Findings' },
  { href: '/methods', label: 'Methods' },
  { href: '/data', label: 'Data' },
  { href: '/about', label: 'About' },
];
const LEGAL = [
  { href: '/privacy', label: 'Privacy' },
  { href: '/terms', label: 'Terms of use' },
  { href: '/cookies', label: 'Cookies and storage' },
  { href: '/accessibility', label: 'Accessibility' },
];
const BAR = [
  { href: '/check', label: 'Check a file' },
  { href: '/blink', label: 'What a blink does' },
  { href: '/devices', label: 'Headsets' },
  { href: '/findings', label: 'Findings' },
];

export function SiteHeader() {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const sheetRef = useRef<HTMLElement>(null);
  const toggleRef = useRef<HTMLButtonElement>(null);

  useEffect(() => setOpen(false), [path]);
  useEffect(() => {
    if (!open) { document.body.style.overflow = ''; return; }
    document.body.style.overflow = 'hidden';
    sheetRef.current?.querySelector<HTMLElement>('a, button')?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setOpen(false); toggleRef.current?.focus(); }
      if (e.key === 'Tab' && sheetRef.current) {
        const f = sheetRef.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
        if (!f.length) return;
        const a = f[0], z = f[f.length - 1];
        if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
        else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
      }
    };
    const mq = window.matchMedia('(min-width: 48em)');
    const onWide = (m: MediaQueryListEvent) => { if (m.matches) setOpen(false); };
    document.addEventListener('keydown', onKey);
    mq.addEventListener('change', onWide);
    return () => {
      document.removeEventListener('keydown', onKey);
      mq.removeEventListener('change', onWide);
      document.body.style.overflow = '';
    };
  }, [open]);

  const cur = (href: string) => (path === href ? 'page' : undefined);
  let i = 0;
  const item = (l: { href: string; label: string }) => (
    <Link key={l.href} href={l.href} aria-current={cur(l.href)} style={{ ['--i' as string]: i++ }}>{l.label}</Link>
  );

  return (
    <>
      <header className="wrap bar">
        <Link href="/" className="bar__mark">EEG Artifact Scope</Link>
        <nav className="bar__links" aria-label="Site">
          {BAR.map((l) => <Link key={l.href} href={l.href} aria-current={cur(l.href)}>{l.label}</Link>)}
          <ThemeToggle />
        </nav>
        <div className="bar__phone">
          <ThemeToggle />
          <button ref={toggleRef} type="button" className="textbtn" onClick={() => setOpen((v) => !v)}
            aria-expanded={open} aria-controls="menu">
            Menu
          </button>
        </div>
      </header>

      <nav id="menu" ref={sheetRef} className="sheet" hidden={!open} aria-label="Menu">
        <div className="sheet__top">
          <span className="bar__mark">EEG Artifact Scope</span>
          <button type="button" className="textbtn" onClick={() => { setOpen(false); toggleRef.current?.focus(); }}>Close</button>
        </div>
        <div className="sheet__cols">
          <div><p>The tool</p>{TOOLS.map(item)}</div>
          <div>
            <p>The work</p>
            {item({ href: '/', label: 'Home' })}
            {READ.map(item)}
            <p style={{ marginTop: '1.2rem' }}>Legal</p>
            {LEGAL.map(item)}
          </div>
        </div>
        <p className="small" style={{ color: 'var(--muted)' }}>A student research project, not a medical device.</p>
      </nav>
    </>
  );
}

export function SiteFooter() {
  return (
    <footer className="wrap close">
      <p className="close__mark">EEG Artifact Scope</p>
      <p>
        This is a student research project, not a medical device. It is not approved by any
        regulator and must not be used to diagnose, treat, or make decisions about any person.
        Nothing you load here is uploaded. See the <Link href="/terms">terms of use</Link> before
        relying on any number it gives you.
      </p>
      <nav className="close__meta" aria-label="The tool">
        {TOOLS.map((l) => <Link key={l.href} href={l.href}>{l.label}</Link>)}
      </nav>
      <nav className="close__meta" aria-label="The work, legal and code">
        {READ.map((l) => <Link key={l.href} href={l.href}>{l.label}</Link>)}
        {LEGAL.map((l) => <Link key={l.href} href={l.href}>{l.label}</Link>)}
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope">Source on GitHub</a>
        <a href="https://github.com/aaryavvatts-lab/eeg-artifact-scope/blob/main/SCORECARD.md">Validation scorecard</a>
      </nav>
      <p className="small" style={{ color: 'var(--muted)' }}>
        Pictures: the blink, spectrum and artifact figures are drawn from this project&apos;s own
        data files. The EEG cap photograph is{' '}
        <a href="https://commons.wikimedia.org/wiki/File:Iss030e116908.jpg">astronaut Andr&eacute; Kuipers
        wearing an electrode cap</a>, NASA, public domain, via Wikimedia Commons. Type is Erode by
        Indian Type Foundry, under the ITF Free Font License, served from this site.
      </p>
    </footer>
  );
}
