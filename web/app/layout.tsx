import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EEG Artifact Scope',
  description:
    'Check EEG signal quality in your browser. Detects blinks, jaw clenches, drift and bad channels — the recording never leaves your machine.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
