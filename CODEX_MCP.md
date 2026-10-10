# Codex MCP für macOS Monterey 12 / Live 11 Standard

## Was funktioniert

Der integrierte MCP-Server nutzt die vorhandene Live-11-Python-Remote-Script-Brücke. Er ist **schreibgeschützt** und benötigt keine zusätzlichen Python-Pakete, Ollama oder Max for Live. Codex kann den aktuellen Set-Zustand lesen, Spuren/Geräte zusammenfassen und geplante Aktionen syntaktisch prüfen. Er kann noch keine Clips oder Arrangements über MCP verändern; hierfür sind weitere Live-seitige Funktionen und eine sichere Bestätigungsoberfläche nötig.

## Installation auf dem Mac

1. GitHub-Branch `feature/macbook-2015-live11` auschecken.
2. `bash scripts/check_mac.command` ausführen; Python 3 und Tkinter für die Desktop-App prüfen.
3. Die bestehende Remote-Brücke einmal über `bash scripts/start_mac.command` installieren: **Ableton-Brücke installieren**, User Library auswählen. App danach beenden.
4. Live 11 neu starten. Einstellungen → Link/Tempo/MIDI → Bedienoberfläche `AbletonPromptBridge`, Ein- und Ausgang **None**. Die User Library liegt normalerweise unter `~/Music/Ableton/User Library`.
5. `bash scripts/setup_codex_mcp.command` ausführen, danach `codex` starten.
6. In Codex `/mcp` aufrufen und `ableton-control` prüfen. Beispielauftrag: „Lies mein aktuelles Ableton-Set und beschreibe eine mögliche Songstruktur, ohne Änderungen vorzunehmen.“

**Wichtig:** `app.py` und `mcp_server.py` verwenden beide Port 8765. Sie dürfen **nicht gleichzeitig** laufen. Codex startet den MCP-Server selbst. Die Live-Brücke verbindet sich mit dem gerade laufenden Server. Bei Verbindungsproblemen Live neu starten und andere Instanzen schließen.

## Sicherheitsmodell

- MCP stellt nur `ableton_status`, `ableton_track_summary` und `ableton_validate_plan` bereit.
- Keine MCP-Schreibaktionen, keine Dateiänderungen, keine Shell-Tools über diesen Server.
- Das bisherige Desktop-Programm kann bestätigte Aktionen weiterhin ausführen, jedoch nicht parallel zum MCP-Server.
- Bevor du das System produktiv nutzt, kopiere dein Live-Set und teste mit einem leeren Projekt.
- Live 11 Standard enthält nicht alle Suite-Instrumente oder Max for Live standardmäßig. Diese MCP-Version benötigt Max for Live nicht.

## Fehlerbehebung

- `codex mcp list` zeigt die Registrierung.
- Bei Portfehlern Desktop-App schließen.
- Falls `AbletonPromptBridge` nicht in Live auftaucht: User-Library-Pfad, Ordnerstruktur und Live-Neustart prüfen.
- Bei `connected: false`: Live muss laufen und das Script als Control Surface aktiviert sein.
- Keine Kompatibilität auf realem Monterey-12-Mac mit Live 11 Standard bestätigt; zunächst vor Ort testen.
