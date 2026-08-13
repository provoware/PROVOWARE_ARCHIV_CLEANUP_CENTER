#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
command -v python3 >/dev/null 2>&1 || { echo "FEHLER: python3 fehlt."; exit 12; }
echo "PROVOWARE Archiv & Cleanup Center — grafischer READ-ONLY Start"
python3 -S app.py --selfcheck
exec python3 -S app.py
