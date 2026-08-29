/**
 * Runs the eegscope analysis inside a Web Worker.
 *
 * Everything here happens on the user's machine. The EEG file is read from a
 * local ArrayBuffer into Pyodide's virtual filesystem and never touches the
 * network -- which is the whole reason the app is a static export with no
 * backend. It also sidesteps Vercel's 4.5 MB request-body limit, which real
 * EEG files (50-234 MB) blow past immediately.
 *
 * A classic worker rather than a module worker: Pyodide loads its own WASM and
 * package bundles, and importScripts keeps that away from the Next.js bundler.
 */

const PYODIDE_VERSION = 'v0.28.3';
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/`;

let pyodide = null;
let ready = null;

function post(stage, detail, extra = {}) {
  self.postMessage({ type: 'progress', stage, detail, ...extra });
}

async function boot(wheelUrl) {
  post('runtime', 'Starting the Python runtime…');
  importScripts(`${PYODIDE_URL}pyodide.js`);
  pyodide = await loadPyodide({ indexURL: PYODIDE_URL });

  // numpy and scipy are needed for every file. scikit-learn is only needed for
  // ICA, so it is loaded lazily rather than paid for on first render.
  post('packages', 'Loading numpy and scipy…');
  await pyodide.loadPackage(['numpy', 'scipy', 'micropip']);

  post('install', 'Installing the analysis package…');
  const micropip = pyodide.pyimport('micropip');
  await micropip.install(wheelUrl);

  post('ready', 'Ready.');
  return pyodide;
}

self.onmessage = async (event) => {
  const { cmd } = event.data || {};

  try {
    if (cmd === 'init') {
      ready = ready || boot(event.data.wheelUrl);
      await ready;
      self.postMessage({ type: 'ready' });
      return;
    }

    if (cmd === 'analyse') {
      const { buffer, filename } = event.data;
      ready = ready || boot(event.data.wheelUrl);
      await ready;

      post('reading', `Reading ${filename}…`);
      const bytes = new Uint8Array(buffer);
      pyodide.FS.writeFile('/tmp/upload.bin', bytes);

      post('analysing', 'Detecting artifacts…');
      pyodide.globals.set('upload_name', filename);

      const result = await pyodide.runPythonAsync(`
import json
from eegscope.web import analyse_for_web

with open("/tmp/upload.bin", "rb") as fh:
    _raw = fh.read()

analyse_for_web(_raw, upload_name)
      `);

      // Free the copy in the virtual filesystem; the browser tab may hold a
      // 200 MB recording and we do not want two of them.
      try {
        pyodide.FS.unlink('/tmp/upload.bin');
      } catch (e) {
        /* not fatal */
      }

      self.postMessage({ type: 'result', payload: JSON.parse(result) });
      return;
    }

    throw new Error(`unknown command: ${cmd}`);
  } catch (err) {
    // Pyodide surfaces Python exceptions with the traceback in .message.
    const message = String(err && err.message ? err.message : err);
    const lines = message.trim().split('\n');
    self.postMessage({
      type: 'error',
      message: lines[lines.length - 1] || message,
      detail: message,
    });
  }
};
