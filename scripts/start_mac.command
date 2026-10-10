#!/bin/bash
# Ableton Control — macOS launcher (works without Homebrew)
set -e
cd "$(dirname "$0")/.."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 mit Tkinter wird benötigt. Siehe README."
  read -r -p "Enter zum Beenden..."
  exit 1
fi
python3 - <<'PY'
import tkinter
print("Tkinter verfügbar")
PY
exec python3 app.py
