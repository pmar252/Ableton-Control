"""Non-blocking loopback HTTP client: no threads and no blocking calls in Live."""
import json
import select
import socket
import time


class LoopbackHTTP:
    def __init__(self, port=8765):
        self.port = port
        self.sock = None

    def start(self, path, token, payload=None):
        if self.sock is not None: raise RuntimeError("Request already active")
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        method = "GET" if payload is None else "POST"
        header = ("%s %s HTTP/1.1\r\nHost: 127.0.0.1:%s\r\nAuthorization: Bearer %s\r\n"
                  "Content-Type: application/json\r\nContent-Length: %s\r\nConnection: close\r\n\r\n") % (method, path, self.port, token, len(body))
        self.output = header.encode("ascii") + body
        self.received = b""
        self.path = path
        self.deadline = time.monotonic() + 3
        self.connecting = True
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setblocking(False)
        self.sock.connect_ex(("127.0.0.1", self.port))

    def close(self):
        if self.sock is not None: self.sock.close()
        self.sock = None

    def poll(self):
        if self.sock is None: return None
        try:
            if time.monotonic() > self.deadline: raise OSError("Bridge timeout")
            ready_r, ready_w, errors = select.select([self.sock], [self.sock] if self.output else [], [self.sock], 0)
            if errors: raise OSError("Socket error")
            if self.connecting and ready_w:
                error = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if error: raise OSError(error, "Bridge connect failed")
                self.connecting = False
            if not self.connecting and ready_w and self.output:
                try:
                    sent = self.sock.send(self.output)
                    self.output = self.output[sent:]
                except BlockingIOError: pass
            if not self.connecting and ready_r:
                try: chunk = self.sock.recv(65536)
                except BlockingIOError: return None
                if not chunk: raise OSError("Connection closed before response")
                self.received += chunk
                if len(self.received) > 1024 * 1024: raise OSError("Response too large")
                if b"\r\n\r\n" in self.received:
                    header, body = self.received.split(b"\r\n\r\n", 1)
                    lines = header.decode("ascii").split("\r\n")
                    status = int(lines[0].split()[1])
                    lengths = [int(line.split(":", 1)[1]) for line in lines[1:] if line.lower().startswith("content-length:")]
                    if not lengths: raise OSError("Missing response length")
                    if len(body) >= lengths[0]:
                        result = (self.path, status, json.loads(body[:lengths[0]].decode("utf-8")))
                        self.close()
                        return result
        except Exception as exc:
            result = (self.path, 0, {"error": str(exc)})
            self.close()
            return result
        return None
