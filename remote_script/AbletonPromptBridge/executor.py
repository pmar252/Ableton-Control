"""Live API operations: invoke ONLY from Live's main thread."""
from .protocol import finite, revision, validate_plan


def unique(items, label):
    matches = [obj for obj in items if obj.name == label]
    if len(matches) != 1:
        raise ValueError("Name fehlt oder ist mehrdeutig: %s" % label)
    return matches[0]


def snapshot(song):
    tracks = []
    for track in song.tracks:
        devices = []
        for device in track.devices:
            devices.append({"name": str(device.name), "parameters": [
                {"name": str(p.name), "value": p.value, "min": p.min, "max": p.max,
                 "quantized": bool(p.is_quantized), "enabled": bool(p.is_enabled)}
                for p in device.parameters]})
        tracks.append({"name": str(track.name), "midi": bool(track.has_midi_input),
                       "solo": bool(track.solo), "mute": bool(track.mute),
                       "arm": bool(track.arm) if track.can_be_armed else None,
                       "volume": track.mixer_device.volume.value, "devices": devices,
                       "occupied_slots": [i for i, s in enumerate(track.clip_slots) if s.has_clip],
                       "slot_count": len(track.clip_slots)})
    state = {"tempo": song.tempo, "playing": bool(song.is_playing), "tracks": tracks}
    return {"state": state, "revision": revision(state)}


def resolve(song, a):
    track = unique(song.tracks, a["track"])
    if a["type"] == "set_arm" and not track.can_be_armed:
        raise ValueError("Spur kann nicht scharfgeschaltet werden")
    if a["type"] == "set_parameter":
        device = unique(track.devices, a["device"])
        parameter = unique(device.parameters, a["parameter"])
        if not parameter.is_enabled:
            raise ValueError("Parameter ist deaktiviert")
        finite(a["value"], parameter.min, parameter.max)
        if parameter.is_quantized and int(a["value"]) != a["value"]:
            raise ValueError("Parameter benötigt eine Ganzzahl")
        return track, parameter
    if a["type"] == "create_midi_clip":
        if not track.has_midi_input:
            raise ValueError("Ziel muss eine MIDI-Spur sein")
        if a["slot"] >= len(track.clip_slots) or track.clip_slots[a["slot"]].has_clip:
            raise ValueError("Clip-Slot fehlt oder ist bereits belegt")
    return track, None


def preflight(song, actions):
    """Check the whole plan before any edit, including references to planned tracks."""
    names = [t.name for t in song.tracks]
    created = {}
    renamed = {}
    planned_clips = set()
    for a in actions:
        kind = a["type"]
        if kind in ("create_audio_track", "create_midi_track"):
            if a["name"] in names:
                raise ValueError("Spurname existiert bereits: %s" % a["name"])
            names.append(a["name"]); created[a["name"]] = kind == "create_midi_track"
        elif "track" in a:
            if names.count(a["track"]) != 1:
                raise ValueError("Spurname fehlt oder ist mehrdeutig: %s" % a["track"])
            if a["track"] not in created:
                # Renamed references are resolved on execution; map them to originals here.
                original = renamed.get(a["track"], a["track"])
                resolve(song, dict(a, track=original))
            elif kind == "set_parameter":
                raise ValueError("Neue Spuren haben noch keine Geräte")
            elif kind == "create_midi_clip":
                if not created[a["track"]] or a["slot"] >= len(song.scenes):
                    raise ValueError("Neuer MIDI-Clip hat kein gültiges Ziel")
            if kind == "create_midi_clip":
                target = (renamed.get(a["track"], a["track"]), a["slot"])
                if target in planned_clips:
                    raise ValueError("Mehrere Clips zielen auf denselben Slot")
                planned_clips.add(target)
            if kind == "rename_track":
                if a["name"] in names:
                    raise ValueError("Neuer Spurname existiert bereits")
                names[names.index(a["track"])] = a["name"]
                if a["track"] in created:
                    created[a["name"]] = created.pop(a["track"])
                renamed[a["name"]] = renamed.pop(a["track"], a["track"])


def apply(song, a):
    kind = a["type"]
    if kind == "set_tempo":
        song.tempo = a["bpm"]
    elif kind in ("create_audio_track", "create_midi_track"):
        getattr(song, kind)(-1)
        song.tracks[-1].name = a["name"]
    elif kind == "play":
        song.start_playing()
    elif kind == "stop":
        song.stop_playing()
    else:
        track, parameter = resolve(song, a)
        if kind == "rename_track": track.name = a["name"]
        elif kind in ("set_solo", "set_mute", "set_arm"): setattr(track, kind[4:], a["enabled"])
        elif kind == "set_volume": track.mixer_device.volume.value = a["value"]
        elif kind == "set_parameter": parameter.value = a["value"]
        elif kind == "create_midi_clip":
            slot = track.clip_slots[a["slot"]]
            slot.create_clip(a["length"])
            slot.clip.name = a["name"]
            if hasattr(slot.clip, "add_new_notes"):
                import Live
                notes = tuple(Live.Clip.MidiNoteSpecification(pitch=n["pitch"], start_time=n["start"], duration=n["duration"], velocity=n["velocity"]) for n in a["notes"])
                slot.clip.add_new_notes(notes)
            else:
                slot.clip.set_notes(tuple((n["pitch"], n["start"], n["duration"], n["velocity"], False) for n in a["notes"]))


def execute(song, job):
    completed = []
    try:
        validate_plan(job["plan"])
        if snapshot(song)["revision"] != job["revision"]:
            raise ValueError("Live-Set hat sich seit dem Vorschlag geändert. Bitte neu planen.")
        actions = job["plan"]["actions"]
        preflight(song, actions)
        song.begin_undo_step()
        try:
            for a in actions:
                apply(song, a)
                completed.append(a)
        finally:
            song.end_undo_step()
        return {"id": job["id"], "ok": True, "completed": len(completed), "snapshot": snapshot(song)}
    except Exception as exc:
        return {"id": job.get("id"), "ok": False, "completed": len(completed),
                "error": str(exc), "message": "Bei Teilfehlern: Live Undo prüfen. Kein automatischer Rollback."}
