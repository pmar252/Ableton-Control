"""Minimal read-only MCP stdio server for Codex and Ableton Live 11.

No third-party Python dependencies. Uses the existing authenticated localhost bridge.
Writes are deliberately not exposed as MCP tools.
"""
import json
import sys
from host import BridgeHost
from remote_script.AbletonPromptBridge.protocol import validate_plan

TOOLS = [
    {"name": "ableton_status", "description": "Read current Ableton connection and set state. Read-only.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "ableton_track_summary", "description": "Summarize tracks, tempo and devices from the current Live set. Read-only.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "ableton_validate_plan", "description": "Validate a proposed action plan without executing it. This never changes Live.",
     "inputSchema": {"type": "object", "properties": {"plan": {"type": "object"}}, "required": ["plan"], "additionalProperties": False}},
]

def result(data, error=False):
    return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}], "isError": error}

def dispatch(host, request):
    method = request.get("method")
    params = request.get("params") or {}
    if method == "initialize":
        return {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                "serverInfo": {"name": "ableton-control-readonly", "version": "0.1.0"}}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name not in {t["name"] for t in TOOLS}:
            return result({"error": "Unknown tool"}, True)
        if name == "ableton_validate_plan":
            try:
                return result({"valid": True, "plan": validate_plan(args["plan"]), "executed": False})
            except (KeyError, ValueError, TypeError) as exc:
                return result({"valid": False, "error": str(exc), "executed": False}, True)
        snap = host.current()
        if snap is None:
            return result({"connected": False, "message": "Live not connected. Install and enable AbletonPromptBridge."})
        state = snap["state"]
        if name == "ableton_status":
            return result({"connected": True, "revision": snap["revision"], "state": state})
        tracks = state.get("tracks", [])
        return result({"connected": True, "tempo": state.get("tempo"),
                       "track_count": len(tracks), "tracks": tracks})
    return None

def main():
    host = BridgeHost()
    try:
        for line in sys.stdin:
            try:
                req = json.loads(line)
                if not isinstance(req, dict):
                    continue
                response = dispatch(host, req)
                if "id" not in req:
                    continue
                if response is None:
                    output = {"jsonrpc": "2.0", "id": req["id"],
                              "error": {"code": -32601, "message": "Method not found"}}
                else:
                    output = {"jsonrpc": "2.0", "id": req["id"], "result": response}
            except Exception as exc:
                output = {"jsonrpc": "2.0", "id": req.get("id") if isinstance(req, dict) else None,
                          "error": {"code": -32603, "message": str(exc)}}
            sys.stdout.write(json.dumps(output, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    finally:
        host.close()

if __name__ == "__main__":
    main()
