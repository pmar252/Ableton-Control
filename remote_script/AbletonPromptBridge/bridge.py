"""Live main-thread bridge. Uses non-blocking sockets, not embedded-Python threads."""
import json
import os
import time
from _Framework.ControlSurface import ControlSurface
from .executor import execute, snapshot
from .http_client import LoopbackHTTP

TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".ableton-prompt-bridge", "token")


class PromptBridge(ControlSurface):
    def __init__(self, c_instance):
        super(PromptBridge, self).__init__(c_instance)
        self._closed = False
        self._client = LoopbackHTTP()
        self._counter = 0
        self._events = []
        self._active_event = None
        self._retry_after = 0
        self.schedule_message(1, self._tick)
        self.show_message("Ableton Prompt Bridge bereit — Desktop-App starten")

    def _tick(self):
        if self._closed: return
        try:
            self._counter += 1
            response = self._client.poll()
            if response:
                path, status, data = response
                if status == 0:
                    if self._active_event and self._active_event["type"] == "result":
                        self._events.insert(0, self._active_event)
                    self._retry_after = time.monotonic() + 1
                elif status == 200 and path == "/bridge/next" and data:
                    if data.get("expires", 0) < time.time():
                        result = {"id": data["id"], "ok": False, "error": "Auftrag abgelaufen", "completed": 0}
                    else:
                        result = execute(self.song(), data)
                    self._events.insert(0, {"type": "result", "result": result})
                self._active_event = None
            if self._counter % 10 == 0:
                # Keep the latest state only; execution results take priority.
                self._events = [event for event in self._events if event["type"] != "snapshot"]
                self._events.append({"type": "snapshot", "snapshot": snapshot(self.song())})
            if self._client.sock is None and time.monotonic() >= self._retry_after:
                try:
                    with open(TOKEN_FILE, "r") as handle: token = handle.read().strip()
                    self._active_event = self._events.pop(0) if self._events else None
                    self._client.start("/bridge/event" if self._active_event else "/bridge/next", token, self._active_event)
                except OSError:
                    self._retry_after = time.monotonic() + 1
        except Exception as exc:
            self.log_message("Prompt Bridge: " + str(exc))
        self.schedule_message(1, self._tick)

    def disconnect(self):
        self._closed = True
        self._client.close()
        super(PromptBridge, self).disconnect()
