"""Deterministic offline commands for older Macs without Ollama."""
import re
from remote_script.AbletonPromptBridge.protocol import validate_plan

def generate_offline_plan(prompt, snapshot):
    text = prompt.strip()
    actions = []
    # Only unambiguous single commands; no fuzzy execution.
    tempo = re.fullmatch(r"(?:setze (?:das )?tempo auf|tempo)\s+(\d+(?:[.,]\d+)?)\s*(?:bpm)?[.!]?\s*", text, re.I)
    midi = re.fullmatch(r"(?:erstelle|lege)\s+(?:eine?\s+)?midi[- ]spur\s+(?:namens\s+)?([\w äöüÄÖÜß-]+?)[.!]?\s*", text, re.I)
    audio = re.fullmatch(r"(?:erstelle|lege)\s+(?:eine?\s+)?audio[- ]spur\s+(?:namens\s+)?([\w äöüÄÖÜß-]+?)[.!]?\s*", text, re.I)
    play = re.fullmatch(r"(?:play|start|starte wiedergabe|spiele ab)[.!]?\s*", text, re.I)
    stop = re.fullmatch(r"(?:stop|stopp|stoppe wiedergabe)[.!]?\s*", text, re.I)
    if tempo:
        actions = [{"type":"set_tempo","bpm":float(tempo.group(1).replace(",","."))}]
    elif midi:
        actions = [{"type":"create_midi_track","name":midi.group(1).strip()}]
    elif audio:
        actions = [{"type":"create_audio_track","name":audio.group(1).strip()}]
    elif play:
        actions = [{"type":"play"}]
    elif stop:
        actions = [{"type":"stop"}]
    summary = ("Offline-Vorschlag: eine Aktion. Vor Ausführung prüfen." if actions else
               "Offline-Modus: Bitte einen einzelnen eindeutigen Befehl verwenden: Tempo 120, Erstelle MIDI-Spur namens Bass, Erstelle Audio-Spur namens Vocals, Play oder Stop. Für komplexe Aufträge ist eine kompatible KI-Anbindung erforderlich.")
    return validate_plan({"summary":summary,"actions":actions})
