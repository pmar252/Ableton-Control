import unittest
from unittest.mock import Mock
from mcp_server import dispatch

class MCPTests(unittest.TestCase):
    def setUp(self):
        self.host = Mock()
        self.host.current.return_value = {"revision": "abc", "state": {"tempo": 120, "tracks": [{"name": "Bass", "devices": []}]}}
    def test_initialize(self):
        self.assertEqual(dispatch(self.host, {"method": "initialize"})["serverInfo"]["name"], "ableton-control-readonly")
    def test_tool_list_is_read_only(self):
        tools = dispatch(self.host, {"method": "tools/list"})["tools"]
        self.assertEqual({t["name"] for t in tools}, {"ableton_status", "ableton_track_summary", "ableton_validate_plan"})
    def test_status(self):
        response = dispatch(self.host, {"method": "tools/call", "params": {"name": "ableton_status"}})
        self.assertIn('"connected": true', response["content"][0]["text"])
    def test_disconnected(self):
        self.host.current.return_value = None
        response = dispatch(self.host, {"method": "tools/call", "params": {"name": "ableton_status"}})
        self.assertIn('"connected": false', response["content"][0]["text"])
    def test_invalid_plan(self):
        response = dispatch(self.host, {"method": "tools/call", "params": {"name": "ableton_validate_plan", "arguments": {"plan": {"summary": "unsafe", "actions": [{"type": "delete_track"}]}}}})
        self.assertTrue(response["isError"])
if __name__ == "__main__":
    unittest.main()
