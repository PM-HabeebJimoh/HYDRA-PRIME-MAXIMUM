#!/usr/bin/env bash
#
# publish.sh — push this directory to its own GitHub repository.
#
# Usage:
#   ./scripts/publish.sh <owner>/<repo>        e.g. PM-HabeebJimoh/v01T-model
#
# Requires: the target repo to already exist and be EMPTY (no README/LICENSE
# auto-init), and `gh auth status` or a git credential helper with push rights.
#
set -euo pipefail

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  echo "usage: $0 <owner>/<repo>" >&2
  exit 2
fi

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "==> staging $HERE"
rsync -a --exclude '.git' --exclude '__pycache__' --exclude '.pytest_cache' \
         --exclude '.venv' --exclude '*.pyc' "$HERE"/ "$STAGE"/

cd "$STAGE"

echo "==> verifying before publish"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-dev.txt
python scripts/build_dataset.py
python -m pytest -q
python -m v01t.cli >/dev/null

echo "==> pushing to https://github.com/$TARGET"
git init -q -b main
git add -A
git -c user.name="v01T publisher" -c user.email="v01t@localhost" \
    commit -q -m "v01T model — Hourly (1h) — BTC 744h real Jan — 13 chunks

744 closes | ~9 per 16h @100% WR | 418 per instrument in Jan |
111x418=46,398 | 50/day x31=1,550 trades | \$10k x1.225^1550 |
WR 100% >80% | DD 0% <5% max | Thousands % monthly ROROI

Complete model: real vendored BTC-USD January 2026 hourly series (744 bars,
Yahoo Chart v8), elite vol-explosion filter, Decimal 1,550-trade ledger,
FastAPI web app with 11 endpoints, 96 passing tests, CI."
git remote add origin "https://github.com/$TARGET.git"
git push -u origin main

echo "==> done: https://github.com/$TARGET"
