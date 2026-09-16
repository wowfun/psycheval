"""Local Chat Completions fixture shared by unit and native Trial checks."""

import json
import threading
import time
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@contextmanager
def judge_server():
    state = {
        "requests": [],
        "counts": Counter(),
        "behavior": {},
        "active": 0,
        "peak": 0,
    }
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            context = json.loads(request["messages"][-1]["content"])
            rubric = context["rubric"]["id"]
            with lock:
                state["requests"].append(request)
                state["counts"][rubric] += 1
                attempt = state["counts"][rubric]
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
            behavior = state["behavior"].get(rubric, {})
            try:
                if state.get("barrier") is not None:
                    state["barrier"].wait(timeout=5)
                delay = behavior.get("delay", 0)
                time.sleep(delay[attempt - 1] if isinstance(delay, list) else delay)
                code = behavior.get("status", 200)
                if behavior.get("retry") and attempt == 1:
                    code = behavior["retry"]
                result = {
                    "id": rubric,
                    "passed": behavior.get("passed", True),
                    "reason": "本地证据判定",
                }
                result.update(behavior.get("result", {}))
                payload = {
                    "choices": [
                        {
                            "finish_reason": behavior.get("finish_reason", "stop"),
                            "message": {
                                "content": behavior.get(
                                    "content", json.dumps(result, ensure_ascii=False)
                                )
                            },
                        }
                    ],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 8},
                }
                data = behavior.get("raw", json.dumps(payload)).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            finally:
                with lock:
                    state["active"] -= 1

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    state["url"] = f"http://127.0.0.1:{server.server_port}/v1"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
