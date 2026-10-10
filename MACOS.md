# Ableton Control auf dem MacBook Pro Retina 2015 (Ableton Live 11)

Dies ist die macOS-Erweiterung der bestehenden lokalen Alpha-Version, **kein fertiger autonomer Musikproduzent**. Auf einem echten MacBook 2015 wurde sie noch nicht getestet.

## Voraussetzungen

- macOS-Version prüfen: Apple-Menü → Über diesen Mac. Installiere eine **zu deiner macOS-Version passende** Python-3-Version von python.org, einschließlich Tkinter. Nicht jede aktuelle Python-/Ollama-Version unterstützt ältere macOS-Versionen.
- Ableton Live 11 und ausreichend freier Arbeitsspeicher.
- **Monterey 12:** Aktuelle Ollama-Versionen benötigen macOS 14 oder neuer. Daher startet diese Mac-Version standardmäßig mit dem eingebauten **offline**-Befehlsplaner. Keine Ollama-Installation erforderlich. Ältere Ollama-Versionen nur nach gesonderter Kompatibilitäts- und Sicherheitsprüfung verwenden.

## Start

1. Repository als ZIP laden und entpacken oder `git clone https://github.com/pmar252/Ableton-Control.git` verwenden.
2. Im Terminal im Projektordner: `bash scripts/check_mac.command`.
3. `bash scripts/start_mac.command` ausführen. Für den Offline-Modus ist Ollama nicht erforderlich.
4. In der Oberfläche **offline** eingestellt lassen. Der Offline-Modus unterstützt einzelne Befehle wie `Tempo 120`, `Erstelle MIDI-Spur namens Bass`, `Erstelle Audio-Spur namens Vocals`, `Play` und `Stop`.
5. Auf **Ableton-Brücke installieren** klicken und **genau die User Library** auswählen, die Live unter Einstellungen → Library zeigt.
6. Live **komplett neu starten**. Unter Einstellungen → Link/Tempo/MIDI bei **Control Surface** `AbletonPromptBridge` auswählen; Ein-/Ausgang auf None.
7. Sobald **Ableton verbunden** angezeigt wird: Auftrag eingeben → Vorschlag erstellen → Aktionen prüfen → In Live ausführen.

Wenn die Control Surface nicht erscheint, prüfe die Remote-Script-Installation. Ableton-Versionen und macOS-Setups können unterschiedliche Script-Suchpfade nutzen; der User-Library-Pfad ist nicht in jeder Konfiguration ein gültiger Control-Surface-Pfad. Prüfe die offizielle Ableton-Anleitung zu Third-Party Remote Scripts.

## Sicherheit und Grenzen

- Vor dem ersten Test das Live-Set unter neuem Namen speichern.
- Die Anwendung steuert Ableton lokal; ChatGPT in diesem Gespräch ist **nicht direkt** mit der laufenden Desktop-App verbunden.
- Die KI erstellt nur Aktionsvorschläge, die das vorhandene Protokoll unterstützt. Es wird kein beliebiger Python-Code in Live ausgeführt.
- Aktuell: Spuren, Tempo, Session-MIDI-Clips, Transport, Mute/Solo/Arm, Lautstärke und Parameter bereits geladener Geräte.
- Noch nicht implementiert: Audio-/Frequenzanalyse, automatisches Arrangement in der Arrangement-Ansicht, Sample-Import, Plugins laden, Mix-/Mastering-Automatik oder direkte ChatGPT-Cloud-Anbindung.
- Bei Ausführungsfehlern können Teiländerungen verbleiben. Live Undo prüfen.
- Für spätere Ausbaustufen: lesende Audioanalyse, Arrangement-Vorschläge, Vorschau/Diff, schrittweise bestätigte Schreibaktionen und Mac-Integrationstests.

## Fehlerbehebung

- **Tkinter fehlt**: macOS-kompatibles Python mit Tkinter installieren und `python3 -m tkinter` testen.
- **Ollama nicht erreichbar**: Für Monterey 12 das Modellfeld auf `offline` stellen. Die aktuelle Ollama-Version ist mit Monterey nicht kompatibel.
- **Keine Verbindung**: Live-Neustart, Control Surface, korrekten Remote-Script-Pfad und lokalen Port 8765 prüfen.
- **Langsam**: Offline-Modus verwenden und andere speicherintensive Apps schließen.
