import json
import tempfile
import time
import unittest
from types import SimpleNamespace as NS
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import patch
from host import BridgeHost
from remote_script.AbletonPromptBridge.protocol import validate_plan
from remote_script.AbletonPromptBridge.executor import execute, snapshot
from remote_script.AbletonPromptBridge.http_client import LoopbackHTTP


class Slot:
    has_clip = False
    def create_clip(self, length):
        if self.has_clip: raise ValueError("Occupied")
        self.has_clip = True
        self.clip = NS(name="", length=length, notes=[])
        self.clip.set_notes = lambda notes: setattr(self.clip, "notes", list(notes))


def track(name, midi=True):
    parameter = NS(name="Threshold", value=0.5, min=0, max=1, is_enabled=True, is_quantized=False)
    return NS(name=name, has_midi_input=midi, can_be_armed=True, arm=False, solo=False, mute=False,
              mixer_device=NS(volume=NS(value=0.7)), devices=[NS(name="Compressor", parameters=[parameter])],
              clip_slots=[Slot() for _ in range(4)])


class Song:
    def __init__(self):
        self.tracks = [track("Bass")]
        self.scenes = [None] * 4
        self.tempo = 120
        self.is_playing = False
        self.undo_open = False
    def create_midi_track(self, index): self.tracks.append(track("New"))
    def create_audio_track(self, index): self.tracks.append(track("New", False))
    def start_playing(self): self.is_playing = True
    def stop_playing(self): self.is_playing = False
    def begin_undo_step(self): self.undo_open = True
    def end_undo_step(self): self.undo_open = False


def plan(actions): return {"summary": "Test", "actions": actions}
def job(song, actions): return {"id": "test", "plan": plan(actions), "revision": snapshot(song)["revision"]}
def clip_action(track_name="Bass"):
    return {"type": "create_midi_clip", "track": track_name, "slot": 0, "length": 4, "name": "Pattern",
            "notes": [{"pitch": 36, "start": 0, "duration": 0.5, "velocity": 100}]}


class ExecutorTests(unittest.TestCase):
    def test_track_tempo_solo_and_notes(self):
        song = Song()
        actions = [{"type": "create_midi_track", "name": "Lead"}, {"type": "set_tempo", "bpm": 118},
                   {"type": "set_solo", "track": "Lead", "enabled": True}, clip_action("Lead")]
        result = execute(song, job(song, actions))
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["completed"], 4)
        self.assertTrue(song.tracks[-1].solo)
        self.assertEqual(song.tracks[-1].clip_slots[0].clip.notes[0][0], 36)
        self.assertFalse(song.undo_open)

    def test_stale_state_prevents_edit(self):
        song = Song(); queued = job(song, [{"type": "set_tempo", "bpm": 100}])
        song.tracks[0].name = "Changed"
        self.assertFalse(execute(song, queued)["ok"])
        self.assertEqual(song.tempo, 120)

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError): validate_plan(plan([{"type": "run_shell", "command": "bad"}]))

    def test_nonfinite_or_boolean_tempo_rejected(self):
        for value in (float("nan"), float("inf"), True, 500):
            with self.assertRaises(ValueError): validate_plan(plan([{"type": "set_tempo", "bpm": value}]))

    def test_parameter_preflight_before_other_edits(self):
        song = Song()
        actions = [{"type": "set_tempo", "bpm": 90}, {"type": "set_parameter", "track": "Bass", "device": "Compressor", "parameter": "Threshold", "value": 99}]
        result = execute(song, job(song, actions))
        self.assertFalse(result["ok"])
        self.assertEqual(song.tempo, 120)

    def test_occupied_and_duplicate_clips_rejected(self):
        song = Song(); song.tracks[0].clip_slots[0].create_clip(4)
        self.assertFalse(execute(song, job(song, [clip_action()]))["ok"])
        song = Song()
        result = execute(song, job(song, [clip_action(), clip_action()]))
        self.assertFalse(result["ok"])
        self.assertFalse(song.tracks[0].clip_slots[0].has_clip)

    def test_ambiguous_name_rejected(self):
        song = Song(); song.tracks.append(track("Bass"))
        result = execute(song, job(song, [{"type": "set_solo", "track": "Bass", "enabled": True}]))
        self.assertFalse(result["ok"])

    def test_rename_and_following_reference(self):
        song = Song()
        result = execute(song, job(song, [{"type": "rename_track", "track": "Bass", "name": "Sub"}, {"type": "set_solo", "track": "Sub", "enabled": True}]))
        self.assertTrue(result["ok"], result)
        self.assertTrue(song.tracks[0].solo)

    def test_modern_midi_api(self):
        song = Song(); slot = song.tracks[0].clip_slots[0]
        original = slot.create_clip
        def create(length):
            original(length)
            slot.clip.add_new_notes = lambda notes: setattr(slot.clip, "notes", notes)
        slot.create_clip = create
        fake_live = NS(Clip=NS(MidiNoteSpecification=lambda **fields: fields))
        with patch.dict("sys.modules", {"Live": fake_live}):
            result = execute(song, job(song, [clip_action()]))
        self.assertTrue(result["ok"], result)
        self.assertEqual(slot.clip.notes[0]["start_time"], 0)

    def test_failure_reports_partial_without_claiming_success(self):
        song = Song()
        song.start_playing = lambda: (_ for _ in ()).throw(RuntimeError("Live rejected playback"))
        result = execute(song, job(song, [{"type": "set_tempo", "bpm": 95}, {"type": "play"}]))
        self.assertFalse(result["ok"])
        self.assertEqual(result["completed"], 1)
        self.assertFalse(song.undo_open)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.host = BridgeHost(port=0, config_dir=self.tmp.name)
        self.base = "http://127.0.0.1:%s" % self.host.port
    def tearDown(self):
        self.host.close(); self.tmp.cleanup()
    def post(self, payload):
        req = Request(self.base + "/bridge/event", data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + self.host.token})
        with urlopen(req, timeout=2) as response: return response.status

    def test_token_required(self):
        with self.assertRaises(HTTPError) as error: urlopen(self.base + "/bridge/next", timeout=2)
        self.assertEqual(error.exception.code, 401)

    def test_full_job_roundtrip_and_nonblocking_client(self):
        song = Song()
        self.post({"type": "snapshot", "snapshot": snapshot(song)})
        identity = self.host.submit(plan([{"type": "set_tempo", "bpm": 130}]), snapshot(song)["revision"])
        client = LoopbackHTTP(port=self.host.port)
        client.start("/bridge/next", self.host.token)
        deadline = time.monotonic() + 3
        result = None
        while result is None and time.monotonic() < deadline:
            result = client.poll(); time.sleep(0.005)
        self.assertIsNotNone(result)
        self.assertEqual(result[1], 200)
        response = execute(song, result[2])
        self.post({"type": "result", "result": response})
        event = self.host.events.get_nowait()
        self.assertEqual(event["result"]["id"], identity)
        self.assertEqual(self.host.current()["state"]["tempo"], 130)
        self.assertIsNone(self.host.pending)

    def test_disconnected_submit_blocked(self):
        with self.assertRaises(ValueError): self.host.submit(plan([{"type": "play"}]), "none")


if __name__ == "__main__": unittest.main()
