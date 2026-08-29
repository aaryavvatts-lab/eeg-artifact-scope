#!/usr/bin/env bash
# Stage everything the web app needs, then build it.
#
# The wheel and benchmark.json are generated artifacts: the wheel is this
# repo's own Python package (which the browser installs into Pyodide) and
# benchmark.json is the validation output that fills the Device Report Card.
# Both are gitignored, so the deploy has to rebuild them rather than assume
# they are checked in.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Building and staging the eegscope wheel"
# Hashed filename, so the immutable cache header on /wheels/ is safe.
uv run python scripts/stage_wheel.py

echo "==> Checking the staged wheel matches the source"
uv run pytest tests/test_wheel_fresh.py -q

if [ -f outputs/benchmark.json ]; then
  echo "==> Using existing outputs/benchmark.json"
else
  echo "==> No benchmark.json; running validation (needs data/)"
  uv run python -m validate.run_all --quick || {
    echo "!! Validation failed. The site still builds; the Device Report Card"
    echo "!! will be hidden because benchmark.json is absent."
  }
fi
[ -f outputs/benchmark.json ] && cp outputs/benchmark.json web/public/benchmark.json

echo "==> Building the web app"
cd web
npm ci --silent 2>/dev/null || npm install --silent
npm run build
echo "==> Done. Static site in web/out/"
echo
echo "Vercel project root directory must be set to 'web'."
echo "Deploy: cd web && vercel deploy --prod"
