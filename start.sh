#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd "$ROOT"; export PYTHONDONTWRITEBYTECODE=1
echo "============================================================"
echo " PROVOWARE Archiv & Cleanup Center — grafischer Start"
echo " Sicherheitsmodus: nur lesen"
echo "============================================================"
command -v python3 >/dev/null 2>&1 || { echo "FEHLER: python3 fehlt."; exit 12; }
echo "[1/3] Start prüfen"; python3 -S tools/runtime_launcher.py --selfcheck
echo "[2/3] Sicherheit prüfen"; python3 -S tests/test_runtime_instance_receipt.py -q
echo "[3/3] Programm öffnen"; exec python3 -S tools/runtime_launcher.py
