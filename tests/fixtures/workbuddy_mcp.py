"""Local, deterministic MCP nonce tool for opt-in desktop acceptance."""

import json
import sys
from pathlib import Path

for line in sys.stdin.buffer:
    request = json.loads(line)
    if "id" not in request:
        continue
    method = request.get("method")
    if method == "initialize":
        result = {
            "protocolVersion": request["params"]["protocolVersion"],
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "fixture", "version": "1"},
        }
    elif method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "nonce",
                    "description": "Returns the nonce for evaluation acceptance",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                }
            ]
        }
    elif method == "tools/call":
        if len(sys.argv) > 1:
            with Path(sys.argv[1]).open("a", encoding="utf-8") as output:
                output.write(json.dumps(request["params"]) + "\n")
        result = {
            "content": [{"type": "text", "text": "MCP_OK_8d309b"}],
            "isError": False,
        }
    else:
        result = {}
    sys.stdout.buffer.write(
        (
            json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}) + "\n"
        ).encode("utf-8")
    )
    sys.stdout.buffer.flush()
