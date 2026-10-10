#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
PROJECT="$(pwd -P)"
PYTHON="$(command -v python3 || true)"
if [ -z "$PYTHON" ]; then
  echo "Python 3 fehlt. Installiere eine mit macOS Monterey kompatible Python-Version."
  exit 1
fi
"$PYTHON" -m unittest discover -s tests -v
if ! command -v codex >/dev/null 2>&1; then
  echo "Codex nicht im PATH."
  exit 1
fi
echo "Registriere schreibgeschützten Ableton MCP Server ..."
codex mcp add ableton-control -- "$PYTHON" "$PROJECT/mcp_server.py"
echo "Fertig. Starte Live 11 und aktiviere AbletonPromptBridge. Danach Codex neu starten."
echo "Hinweis: Die Desktop-App app.py darf nicht gleichzeitig laufen (Port 8765)."
