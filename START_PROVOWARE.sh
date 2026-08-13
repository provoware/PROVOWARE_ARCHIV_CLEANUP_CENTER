#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ ! -t 0 ]] && command -v konsole >/dev/null 2>&1 && [[ "${PROVOWARE_GUI_RELAUNCHED:-0}" != 1 ]]; then
  PROVOWARE_GUI_RELAUNCHED=1 konsole -e bash "$ROOT/start.sh" >/dev/null 2>&1 &
  exit 0
fi
exec bash "$ROOT/start.sh"
