/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export: the whole app is HTML/JS/WASM on a CDN. There is no server
  // to send an EEG file to, which is the point -- see the privacy note in the
  // README. Also sidesteps Vercel's 4.5 MB request-body cap entirely.
  output: 'export',
  reactStrictMode: true,
  images: { unoptimized: true },
};
export default nextConfig;
