import unittest
from offline_planner import generate_offline_plan

class OfflinePlannerTests(unittest.TestCase):
    def plan(self, prompt):
        return generate_offline_plan(prompt, {"state": {"tempo": 120, "tracks": []}})
    def test_tempo(self):
        self.assertEqual(self.plan("Tempo 125")["actions"], [{"type": "set_tempo", "bpm": 125.0}])
    def test_midi(self):
        self.assertEqual(self.plan("Erstelle MIDI-Spur namens Bass")["actions"][0]["name"], "Bass")
    def test_stop(self):
        self.assertEqual(self.plan("Stop")["actions"], [{"type": "stop"}])
    def test_unsupported_is_noop(self):
        self.assertEqual(self.plan("Lösche alle Spuren")["actions"], [])
    def test_invalid_tempo(self):
        with self.assertRaises(ValueError):
            self.plan("Tempo 999")
if __name__ == "__main__":
    unittest.main()
