"""Strict shared action format. This module never calls Live or a model."""
import hashlib
import json
import math

SCHEMA = '''Return one JSON object: {"summary":"brief German description","actions":[...]}. Supported actions:
{"type":"set_tempo","bpm":120}
{"type":"create_midi_track","name":"Bass"}
{"type":"create_audio_track","name":"Vocals"}
{"type":"rename_track","track":"exact existing name","name":"new name"}
{"type":"set_solo","track":"exact name","enabled":true}
{"type":"set_mute","track":"exact name","enabled":false}
{"type":"set_arm","track":"exact name","enabled":true}
{"type":"set_volume","track":"exact name","value":0.7}
{"type":"set_parameter","track":"exact name","device":"exact existing device name","parameter":"exact existing parameter name","value":0.5}
{"type":"create_midi_clip","track":"exact MIDI track name","slot":0,"length":16,"name":"Bass pattern","notes":[{"pitch":36,"start":0,"duration":0.25,"velocity":100}]}
{"type":"play"}
{"type":"stop"}
Track/device/parameter names must match the supplied state or a track created earlier in this plan.
Volume uses Live's normalized 0..1 parameter, NOT dB. Device parameters use their supplied raw min/max range; never guess a dB/Hz conversion. Clip slot is zero-based, times and length are in quarter-note beats. Never overwrite an occupied slot. A MIDI clip needs an instrument already on its track to sound.
No sample loading, device insertion, file access, sidechain routing, deletion, code execution, or analysis of audio is supported. Do not claim to optimize sound. Never simulate unsupported operations using another operation. If ANY requested task is unsupported, return actions:[] and explain the limitation in summary. Ask for clarification in summary when needed. No markdown or extra text.'''


def finite(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Zahl außerhalb des erlaubten Bereichs: %r" % value)
    return value


def name(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128 or any(ord(c) < 32 for c in value):
        raise ValueError("Ungültiger Name")
    return value


def exact_keys(item, keys):
    if set(item) != set(keys):
        raise ValueError("Ungültige Felder für %s" % item.get("type", "Aktion"))


def validate_plan(data):
    if not isinstance(data, dict) or set(data) != {"summary", "actions"} or not isinstance(data["summary"], str) or len(data["summary"]) > 2000:
        raise ValueError("Ungültiges Planformat")
    actions = data["actions"]
    if not isinstance(actions, list) or len(actions) > 32:
        raise ValueError("Maximal 32 Aktionen pro Auftrag")
    created = 0
    for a in actions:
        if not isinstance(a, dict):
            raise ValueError("Aktion muss ein Objekt sein")
        kind = a.get("type")
        if kind == "set_tempo":
            exact_keys(a, ("type", "bpm")); finite(a["bpm"], 20, 300)
        elif kind in ("create_midi_track", "create_audio_track"):
            exact_keys(a, ("type", "name")); name(a["name"])
            created += 1
            if created > 8:
                raise ValueError("Maximal acht neue Spuren")
        elif kind == "rename_track":
            exact_keys(a, ("type", "track", "name")); name(a["track"]); name(a["name"])
        elif kind in ("set_solo", "set_mute", "set_arm"):
            exact_keys(a, ("type", "track", "enabled")); name(a["track"])
            if not isinstance(a["enabled"], bool):
                raise ValueError("enabled muss true oder false sein")
        elif kind == "set_volume":
            exact_keys(a, ("type", "track", "value")); name(a["track"]); finite(a["value"], 0, 1)
        elif kind == "set_parameter":
            exact_keys(a, ("type", "track", "device", "parameter", "value"))
            for key in ("track", "device", "parameter"):
                name(a[key])
            finite(a["value"], -1e9, 1e9)
        elif kind == "create_midi_clip":
            exact_keys(a, ("type", "track", "slot", "length", "name", "notes"))
            name(a["track"]); name(a["name"]); finite(a["length"], 0.25, 256)
            if type(a["slot"]) is not int or not 0 <= a["slot"] < 256:
                raise ValueError("Ungültiger Clip-Slot")
            if not isinstance(a["notes"], list) or not 1 <= len(a["notes"]) <= 256:
                raise ValueError("Ein Clip benötigt 1–256 Noten")
            for n in a["notes"]:
                if not isinstance(n, dict) or set(n) != {"pitch", "start", "duration", "velocity"}:
                    raise ValueError("Ungültige MIDI-Note")
                for key, lo, hi in (("pitch", 0, 127), ("velocity", 1, 127)):
                    if type(n[key]) is not int:
                        raise ValueError("MIDI-Werte müssen Ganzzahlen sein")
                    finite(n[key], lo, hi)
                finite(n["start"], 0, a["length"]); finite(n["duration"], 0.01, a["length"])
                if n["start"] + n["duration"] > a["length"]:
                    raise ValueError("Note reicht über den Clip hinaus")
        elif kind in ("play", "stop"):
            exact_keys(a, ("type",))
        else:
            raise ValueError("Nicht unterstützte Aktion: %s" % kind)
    return data


def revision(state):
    return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=True, allow_nan=False).encode("utf-8")).hexdigest()
