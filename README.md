# Ableton Control für Windows 11

Eine Desktop-App, mit der du Ableton Live über deutsche oder englische Textaufträge steuern kannst. Die lokale KI erstellt einen Vorschlag aus dem aktuellen Live-Set. Du siehst die genauen Aktionen und führst sie mit einem Klick aus. Die App wartet auf eine Ausführungsbestätigung aus Ableton.

**Status: erste Alpha-Version.** Logik und Verbindung werden automatisiert mit einem simulierten Live-Set getestet. Der Betrieb in einer echten Windows-/Ableton-Installation ist noch nicht verifiziert. Das Projekt ist kein fertiger autonomer Produzent.

## Funktionen

- MIDI- und Audiospuren anlegen und benennen.
- Tempo setzen; Wiedergabe starten oder stoppen.
- Bestehende Spuren umbenennen, Solo/Mute/Arm und Lautstärke ändern.
- Neue MIDI-Clips mit Noten in **leeren Session-Slots** erstellen.
- Parameter **bereits geladener Geräte** über ihre tatsächlichen Namen und Wertebereiche ändern.
- Vorhandene Spuren, Geräte, Parameter und belegte Clip-Slots lesen.

Sample-Auswahl und -Import, neue Instrumente/Effekte laden, Sidechain-Routing, Arrangement-Editing und automatische klangliche EQ-/Compressor-Optimierung sind noch nicht implementiert. Geräte in verschachtelten Racks werden nicht erfasst. Ein neuer MIDI-Clip erzeugt erst Ton, wenn auf der Spur ein Instrument liegt. Solo/Arm folgen außerdem den jeweiligen exklusiven Einstellungen von Live.

## Voraussetzungen

- Windows 11, Ableton Live **11 oder 12**. Die Bridge verwendet ein Remote-Script; **Max for Live ist dafür nicht erforderlich**.
- [Ollama für Windows](https://ollama.com/download/windows) und ein lokales Modell, z. B. `qwen2.5:7b`. RAM/GPU und Modellgröße bestimmen Geschwindigkeit und Antwortqualität. Bei knappem RAM kann ein kleineres Modell verwendet werden.
- Nur beim Start aus dem Quellcode: [Python 3.11+](https://www.python.org/downloads/windows/) mit Tkinter. Die Windows-EXE enthält Python bereits.

Es gibt keine Cloud-API und keinen API-Schlüssel. Prompts und Set-Informationen werden an das lokale Ollama auf `127.0.0.1:11434` übergeben. Zum erstmaligen Herunterladen von Modell und Programmen wird Internet benötigt.

## Einrichtung auf dem Laptop

1. Dieses Repository über **Code → Download ZIP** herunterladen und entpacken.
2. Ollama installieren. In PowerShell einmal ausführen:
   ```powershell
   ollama pull qwen2.5:7b
   ```
3. `scripts/start_windows.bat` doppelklicken. Alternativ die portable Windows-EXE verwenden, sobald ein erfolgreicher GitHub-Actions-Build vorliegt.
4. In der App **Ableton-Brücke installieren** anklicken und deinen **User-Library-Ordner** auswählen. Den richtigen Pfad findest du in Live unter Einstellungen → Library. Der Standardpfad ist `Dokumente/Ableton/User Library`; er kann bei OneDrive oder eigener Konfiguration anders sein.
5. Live neu starten. Einstellungen → MIDI/Link, Tempo & MIDI → **Bedienoberfläche / Control Surface: AbletonPromptBridge**. Für Eingang und Ausgang jeweils **None/Keine** auswählen. Ein physischer MIDI-Controller ist nicht nötig.
6. Die Desktop-App offen lassen. Oben muss **Ableton verbunden** erscheinen.
7. Einen Auftrag eingeben, **Vorschlag erstellen** anklicken, die Liste prüfen und **In Live ausführen** wählen.

Du kannst die Brücke später deaktivieren, indem du in Live die Bedienoberfläche wieder auf None/Keine stellst. Zur vollständigen Entfernung den installierten Ordner `Remote Scripts/AbletonPromptBridge` entfernen. Die Desktop-App ist portabel.

## Beispiele

> Setze das Tempo auf 118 BPM und erstelle eine MIDI-Spur namens Bass.

> Schalte die Spur Bass auf Solo und die Spur Vocals stumm.

> Erstelle auf der bestehenden MIDI-Spur Bass im ersten leeren Session-Slot einen viertaktigen Clip mit einem einfachen Bassmuster in A-Moll. Verändere keine anderen Spuren.

> Setze den vorhandenen Parameter Threshold des vorhandenen Geräts Compressor auf der Spur Bass auf einen Wert innerhalb seines aktuellen Bereichs. Falls dieser nicht eindeutig auf dB abbildbar ist, frage nach.

Die Lautstärke wird derzeit als Live-Parameterwert zwischen 0 und 1 gesetzt, nicht direkt in dB. Parameterwerte anderer Geräte verwenden deren rohe Live-Wertebereiche. Die KI darf keine dB-/Hz-Umrechnung erfinden. Bei nicht unterstützten Aufträgen soll sie einen leeren Aktionsplan und eine Erklärung zurückgeben.

## Windows-EXE erstellen

Das Repository enthält `.github/workflows/windows.yml`. Der Workflow testet das Projekt auf Windows und baut `AbletonControl.exe` mit PyInstaller. Nach einem erfolgreichen Lauf unter **Actions → Windows app and tests → Artifacts → AbletonControl-Windows11** herunterladen und entpacken. GitHub verlangt für Artifact-Downloads eine Anmeldung. Die EXE ist portabel und installiert nur auf deinen Klick hin die Bridge.

Wenn die GitHub-Verbindung das Speichern von Workflow-Dateien nicht erlaubt, kann der Build lokal mit `scripts/build_windows.bat` erfolgen. Dieser installiert PyInstaller in eine projektlokale virtuelle Umgebung. Ergebnis: `dist/AbletonControl.exe`.

## Prüfungen und Grenzen

- Strikte erlaubte Aktionen statt frei ausgeführtem KI-Code.
- Vorprüfung von Namen, Wertebereichen und Clip-Slots vor dem ersten Edit.
- Wenn sich der erfasste Live-Set-Zustand seit dem Vorschlag geändert hat, wird der Auftrag abgelehnt. Dann neu planen.
- Maximal 32 Aktionen, acht neue Spuren und 256 Noten pro Clip.
- Lokale, token-geschützte Verbindung auf `127.0.0.1:8765`. Die Bridge benutzt nicht blockierende Netzwerkzugriffe ohne zusätzliche Threads in Live.
- Ergebnisse bestätigen ausgeführte API-Aufrufe. Bei Fehlern wird gestoppt und die Zahl abgeschlossener Aktionen gemeldet. Es gibt **keinen automatischen Rollback**; mögliche Teiländerungen mit Live Undo prüfen. Die Undo-Gruppierung umfasst Edit-Aktionen; Transportzustände sind nicht zwingend per Undo rückgängig zu machen.
- Vor dem ersten Test eine Kopie des Live-Sets speichern. Limits deiner Live-Edition gelten weiterhin.

## Fehlerbehebung

**Ableton nicht verbunden:** User-Library-Pfad, Remote-Script-Auswahl und Live-Neustart prüfen. Brücke und App müssen unter demselben Windows-Benutzer laufen. Port 8765 darf nicht durch eine andere Anwendung belegt sein. Lade nur eine Instanz der Bridge in Live.

**Modell fehlt / Vorschlag dauert lange:** Ollama starten, `ollama list` prüfen, Modell in der App auswählen. Nach 180 Sekunden endet ein KI-Aufruf mit einer Fehlermeldung.

**Set verändert / Parameter fehlt:** Neuen Vorschlag erzeugen. Spuren und Geräte müssen eindeutig benannt sein. Rack-Untergeräte werden in dieser Version nicht erfasst.

**Auftrag wartet ohne Ergebnis:** Bei Verbindungsabbruch ist der Ausführungsstatus möglicherweise unbekannt. Live prüfen und die Desktop-App neu starten; denselben Auftrag nicht blind erneut ausführen.

## Entwicklung

Runtime ohne externe Python-Pakete. Tests:

```powershell
python -m unittest discover -s tests -v
```

`app.py`: Prompt-Oberfläche und Ollama-Aufruf. `host.py`: lokale Verbindung und Auftragsverwaltung. `remote_script/AbletonPromptBridge`: Kontrolloberfläche, Zustandsabfrage, strikte Aktionsprüfung und Live-Ausführung.

## Technische Quellen

- [Ableton: Remote-Scripte installieren und Python-3-Kompatibilität ab Live 11](https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts)
- [Cycling '74: Song / Live Object Model](https://docs.cycling74.com/apiref/lom/song/)
- [Cycling '74: Clip / Live Object Model](https://docs.cycling74.com/apiref/lom/clip/)
- [AbletonOSC: etablierte ControlSurface- und Tick-Architektur](https://github.com/ideoforms/AbletonOSC)

Der Code dieses Projekts ist eine eigene Implementierung; Ableton Live und Ollama werden nicht mitgeliefert. Eine mögliche spätere Max-for-Live-Oberfläche kann auf dieselbe Aktionsprüfung aufbauen.
