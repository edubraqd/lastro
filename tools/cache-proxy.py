"""Local proxy for Claude Code: per-call usage log + prompt-cache keep-alive.

Forwards every request byte-for-byte to api.anthropic.com and streams the
response back. For /v1/messages it keeps the last request body and headers of
the main conversation; after CACHE_PING_AFTER_MIN idle minutes it re-sends the
same body with max_tokens=1, stream=false (a "ping") to refresh the 1h cache
TTL. Measured 2026-09-14 on 641 sessions: a gap >= 60 min between calls broke
the cache 93-98% of the time; 10-59 min, 8-25%, rising with the gap. Hence the
default ping every 20 min, at most CACHE_PING_MAX times per idle stretch.

Status of the keep-alive: EXPERIMENTAL. Each ping is a cache read of the whole
context (0.1x price), so on a 300k context a ping costs ~30k input-equivalent
tokens. Whether it pays depends on how often you come back after 20-60 min;
the log lets you measure that. The usage logger alone is safe to use always.

    python tools/cache-proxy.py                 # listens on 127.0.0.1:8790
    curl -X POST http://127.0.0.1:8790/_ping    # ping now
    curl http://127.0.0.1:8790/_status

Launch Claude Code through it: tools/wrap-cache.ps1 (Windows) or
tools/wrap-cache.sh. Both set ANTHROPIC_BASE_URL and
_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL=1 -- without the second one Claude
Code treats the proxy as a third-party endpoint and loses the 1M window.

Log: ~/.claude/cache-proxy.log (jsonl, one line per call, real or ping).
Last body without headers: ~/.claude/cache-proxy-last.json (inspection).
"""
import copy, hashlib, http.client, json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST, PORT = "127.0.0.1", int(os.environ.get("CACHE_PROXY_PORT", "8790"))
UPSTREAM = os.environ.get("CACHE_PROXY_UPSTREAM", "api.anthropic.com")
PING_AFTER = float(os.environ.get("CACHE_PING_AFTER_MIN", "20")) * 60
PING_EVERY = float(os.environ.get("CACHE_PING_EVERY_MIN", "20")) * 60
PING_MAX = int(os.environ.get("CACHE_PING_MAX", "9"))
HOME = os.path.expanduser("~")
LOG = os.path.join(HOME, ".claude", "cache-proxy.log")
LAST = os.path.join(HOME, ".claude", "cache-proxy-last.json")
DROP_REQ = {"host", "content-length", "accept-encoding", "connection", "transfer-encoding"}
DROP_RESP = {"transfer-encoding", "content-length", "connection", "content-encoding"}

state = {"body": None, "headers": None, "path": None, "last": 0.0, "pings": 0, "last_ping": 0.0}
lock = threading.Lock()


def log(rec):
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def usage_from(text, stream):
    """Extract usage from an SSE (stream) or JSON response."""
    u = {}
    try:
        if not stream:
            d = json.loads(text)
            return d.get("usage") or {"error": d.get("error")}
        for line in text.splitlines():
            if not line.startswith("data: "):
                continue
            d = json.loads(line[6:])
            t = d.get("type")
            if t == "message_start":
                u.update(d["message"].get("usage") or {})
            elif t == "message_delta":
                u["output_tokens"] = (d.get("usage") or {}).get("output_tokens")
            elif t == "error":
                u["error"] = d.get("error")
    except Exception as e:
        u["parse_error"] = str(e)
    return {k: v for k, v in u.items() if v is not None}


def forward(method, path, headers, body):
    conn = http.client.HTTPSConnection(UPSTREAM, timeout=600)
    conn.request(method, path, body=body, headers=headers)
    return conn, conn.getresponse()


def build_ping(body):
    p = copy.deepcopy(body)
    p["stream"] = False
    p["max_tokens"] = 1
    th = p.get("thinking") or {}
    # max_tokens must exceed the thinking budget; with thinking on the model
    # may spend output before stopping. Logged so it can be measured.
    if th.get("type") == "enabled" and th.get("budget_tokens"):
        p["max_tokens"] = int(th["budget_tokens"]) + 1
    return p


def ping(reason):
    with lock:
        body, headers, path = state["body"], state["headers"], state["path"]
    if not body:
        log({"kind": "ping", "reason": reason, "error": "no body stored"})
        return
    p = build_ping(body)
    raw = json.dumps(p).encode("utf-8")
    h = dict(headers)
    h["content-length"] = str(len(raw))
    t0 = time.time()
    try:
        conn, resp = forward("POST", path, h, raw)
        text = resp.read().decode("utf-8", "replace")
        conn.close()
        log({"kind": "ping", "reason": reason, "status": resp.status, "model": p.get("model"),
             "max_tokens": p["max_tokens"], "thinking": p.get("thinking"),
             "body_sha": hashlib.sha256(raw).hexdigest()[:12],
             "usage": usage_from(text, False), "ms": int((time.time() - t0) * 1000),
             "response": text[:300] if resp.status != 200 else None})
    except Exception as e:
        log({"kind": "ping", "reason": reason, "error": repr(e)})
    with lock:
        state["pings"] += 1
        state["last_ping"] = time.time()


def watchdog():
    while True:
        time.sleep(30)
        with lock:
            idle = time.time() - state["last"]
            since_ping = time.time() - state["last_ping"]
            due = (state["body"] is not None and state["pings"] < PING_MAX
                    and idle >= PING_AFTER and since_ping >= PING_EVERY)
        if due:
            ping(f"idle {idle/60:.0f} min")


class Server(ThreadingHTTPServer):
    # on Windows SO_REUSEADDR lets two copies bind the same port (they steal requests)
    allow_reuse_address = False


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _admin(self):
        if self.path == "/_status":
            with lock:
                s = {k: v for k, v in state.items() if k not in ("body", "headers")}
                s["idle_min"] = round((time.time() - state["last"]) / 60, 1) if state["last"] else None
                s["has_body"] = state["body"] is not None
            self._json(200, s)
            return True
        if self.path == "/_ping":
            threading.Thread(target=ping, args=("manual",), daemon=True).start()
            self._json(200, {"ok": True})
            return True
        return False

    def _json(self, status, obj):
        raw = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self._admin():
            return
        self._proxy("GET")

    def do_POST(self):
        if self._admin():
            return
        self._proxy("POST")

    def _proxy(self, method):
        n = int(self.headers.get("content-length") or 0)
        body = self.rfile.read(n) if n else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in DROP_REQ}
        if body is not None:
            headers["content-length"] = str(len(body))
        headers["accept-encoding"] = "identity"
        is_msg = self.path.startswith("/v1/messages") and "count_tokens" not in self.path and method == "POST"
        parsed = None
        if is_msg:
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
        t0 = time.time()
        try:
            conn, resp = forward(method, self.path, headers, body)
        except Exception as e:
            self._json(502, {"error": {"type": "proxy", "message": repr(e)}})
            log({"kind": "real", "path": self.path, "error": repr(e)})
            return
        self.send_response(resp.status)
        for k, v in resp.getheaders():
            if k.lower() not in DROP_RESP:
                self.send_header(k, v)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        parts = []
        try:
            while True:
                chunk = resp.read1(65536)
                if not chunk:
                    break
                parts.append(chunk)
                self.wfile.write(b"%x\r\n%s\r\n" % (len(chunk), chunk))
                self.wfile.flush()
            self.wfile.write(b"0\r\n\r\n")
            self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            conn.close()
        if not is_msg:
            return
        text = b"".join(parts).decode("utf-8", "replace")
        stream = bool(parsed and parsed.get("stream"))
        with lock:
            # only the main conversation (stream); the Haiku side calls (title,
            # classifier) arrive later and would steal the ping body
            if parsed and resp.status == 200 and parsed.get("stream"):
                state["body"], state["headers"], state["path"] = parsed, headers, self.path
                state["last"] = time.time()
                state["pings"] = 0
                try:
                    with open(LAST, "w", encoding="utf-8") as f:
                        json.dump(parsed, f, ensure_ascii=False)
                except Exception:
                    pass
        log({"kind": "real", "status": resp.status, "model": (parsed or {}).get("model"), "stream": stream,
             "max_tokens": (parsed or {}).get("max_tokens"), "thinking": (parsed or {}).get("thinking"),
             "n_msgs": len((parsed or {}).get("messages") or []),
             "body_sha": hashlib.sha256(body).hexdigest()[:12],
             "usage": usage_from(text, stream), "ms": int((time.time() - t0) * 1000)})


if __name__ == "__main__":
    threading.Thread(target=watchdog, daemon=True).start()
    print(f"cache-proxy on http://{HOST}:{PORT} -> https://{UPSTREAM}  ping after {PING_AFTER/60:.0f} min idle, every {PING_EVERY/60:.0f}, max {PING_MAX}", flush=True)
    Server((HOST, PORT), H).serve_forever()
