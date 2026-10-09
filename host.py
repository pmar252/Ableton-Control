"""Authenticated loopback bridge, shared by source and packaged desktop app."""
import json
import queue
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from remote_script.AbletonPromptBridge.protocol import validate_plan


class BridgeHost:
    def __init__(self, port=8765, config_dir=None):
        self.token = secrets.token_urlsafe(32)
        self.jobs = queue.Queue(maxsize=1)
        self.events = queue.Queue()
        self.lock = threading.Lock()
        self.snapshot = None
        self.last_seen = 0
        self.pending = None
        host = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass

            def respond(self, code, value):
                body = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def authorized(self):
                return secrets.compare_digest(self.headers.get("Authorization", ""), "Bearer " + host.token)

            def do_GET(self):
                if not self.authorized(): return self.respond(401, {"error": "Unauthorized"})
                if self.path != "/bridge/next": return self.respond(404, {})
                try: job = host.jobs.get_nowait()
                except queue.Empty: job = None
                self.respond(200, job)

            def do_POST(self):
                if not self.authorized(): return self.respond(401, {"error": "Unauthorized"})
                if self.path != "/bridge/event": return self.respond(404, {})
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    if not 0 < length <= 1024 * 1024: return self.respond(413, {})
                    event = json.loads(self.rfile.read(length))
                    with host.lock:
                        if event.get("type") == "snapshot":
                            snap = event["snapshot"]
                            if not isinstance(snap.get("state"), dict) or not isinstance(snap.get("revision"), str):
                                raise ValueError("Invalid snapshot")
                            host.snapshot = snap
                            host.last_seen = time.monotonic()
                        elif event.get("type") == "result":
                            result = event["result"]
                            if result.get("id") != host.pending: return self.respond(409, {})
                            host.pending = None
                            if result.get("snapshot"):
                                host.snapshot = result["snapshot"]
                                host.last_seen = time.monotonic()
                            host.events.put(event)
                        else:
                            raise ValueError("Unknown event")
                    self.respond(200, {"ok": True})
                except (ValueError, KeyError, TypeError, AttributeError):
                    self.respond(400, {})

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.port = self.server.server_address[1]
        self.config_dir = Path(config_dir or Path.home() / ".ableton-prompt-bridge")
        self.config_dir.mkdir(parents=True, exist_ok=True)
        token_path = self.config_dir / "token"
        token_path.write_text(self.token, encoding="utf-8")
        token_path.chmod(0o600)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def current(self):
        with self.lock:
            if self.snapshot is None or time.monotonic() - self.last_seen > 5:
                return None
            return self.snapshot

    def submit(self, plan, expected_revision):
        validate_plan(plan)
        if not plan["actions"]: raise ValueError("Keine Aktionen im Vorschlag")
        with self.lock:
            if self.pending: raise ValueError("Ein Auftrag wartet noch auf Ableton. Bei Verbindungsabbruch App neu starten.")
            if self.snapshot is None or time.monotonic() - self.last_seen > 5:
                raise ValueError("Ableton ist nicht verbunden")
            if self.snapshot["revision"] != expected_revision:
                raise ValueError("Live-Set wurde verändert. Bitte neuen Vorschlag erstellen.")
            job = {"id": uuid.uuid4().hex, "plan": plan, "revision": expected_revision, "expires": time.time() + 60}
            self.jobs.put_nowait(job)
            self.pending = job["id"]
            return job["id"]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
