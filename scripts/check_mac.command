#!/bin/bash
cd "$(dirname "$0")/.."
echo "Ableton Control — macOS Diagnose"
sw_vers
echo "Python:"
python3 --version || exit 1
echo "Tkinter:"
python3 -c 'import tkinter; print("OK")' || echo "Tkinter fehlt: Python von python.org installieren"
echo "Ollama:"
if command -v ollama >/dev/null 2>&1; then ollama list; else echo "Nicht im PATH"; fi
echo "Live 11:"
ls -d "/Applications/Ableton Live 11"*.app 2>/dev/null || echo "Nicht unter /Applications gefunden"
echo "Fertig."
read -r -p "Enter zum Beenden..."
