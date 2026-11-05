"""Minimal Chrome DevTools Protocol client over one browser-level WebSocket. Standard library only.

One connection serves every tab (Target.attachToTarget with flatten), so a Chrome that asks
"Allow remote debugging?" on each new connection asks only once.

    browser = connect("main")        # the user's own Chrome/Edge/Chromium, via DevToolsActivePort
    browser = connect("9222")        # a Chrome started with --remote-debugging-port=9222
    session = browser.attach(target_id)
    browser.call("Runtime.evaluate", {...}, session)
"""
import base64
import glob
import json
import os
import socket
import struct
import urllib.parse
import urllib.request

# Where Chromium-based browsers write DevToolsActivePort (port on line 1, /devtools/browser/<id> on line 2)
PROFILE_DIRS = [
    "~/.config/google-chrome", "~/.config/google-chrome-beta", "~/.config/google-chrome-unstable",
    "~/.config/chromium", "~/.config/microsoft-edge", "~/.config/BraveSoftware/Brave-Browser",
    "~/snap/chromium/common/chromium",
    "~/Library/Application Support/Google/Chrome", "~/Library/Application Support/Chromium",
    "~/Library/Application Support/Microsoft Edge", "~/Library/Application Support/BraveSoftware/Brave-Browser",
]


def browser_ws_url(target):
    """`main` = the newest DevToolsActivePort among the usual profiles; a number = a debugging port."""
    if target == "main":
        files = [f for d in PROFILE_DIRS for f in glob.glob(os.path.join(os.path.expanduser(d), "DevToolsActivePort"))]
        if not files:
            raise RuntimeError("no DevToolsActivePort found: open chrome://inspect/#remote-debugging and turn on "
                               "remote debugging, or start the browser with --remote-debugging-port")
        port, path = open(max(files, key=os.path.getmtime)).read().split("\n")[:2]
        return f"ws://127.0.0.1:{port.strip()}{path.strip()}"
    if target.startswith("ws://"):
        return target
    with urllib.request.urlopen(f"http://127.0.0.1:{int(target)}/json/version", timeout=5) as r:
        return json.load(r)["webSocketDebuggerUrl"]


class WebSocket:
    def __init__(self, url, timeout):
        u = urllib.parse.urlparse(url)
        self.sock = socket.create_connection((u.hostname, u.port or 80), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f"GET {u.path or '/'} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\n"
                           "Upgrade: websocket\r\nConnection: Upgrade\r\n"
                           f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        head = b""
        while b"\r\n\r\n" not in head:          # blocks here while the user answers the approval prompt
            c = self.sock.recv(4096)
            if not c:
                raise ConnectionError("browser closed the connection (approval denied?)")
            head += c
        status = head.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise ConnectionError(f"websocket upgrade refused: {status.decode(errors='replace')}")
        self.buf = head.split(b"\r\n\r\n", 1)[1]

    def _read(self, n):
        while len(self.buf) < n:
            c = self.sock.recv(65536)
            if not c:
                raise ConnectionError("connection closed")
            self.buf += c
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def send(self, text, opcode=0x1):
        data = text.encode() if isinstance(text, str) else text
        n = len(data)
        head = bytes([0x80 | opcode])
        if n < 126:
            head += bytes([0x80 | n])
        elif n < 65536:
            head += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            head += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(head + mask + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def recv(self):
        parts = []
        while True:
            b0, b1 = self._read(2)
            op, n = b0 & 0x0F, b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            mask = self._read(4) if b1 & 0x80 else None
            data = self._read(n)
            if mask:
                data = bytes(b ^ mask[i % 4] for i, b in enumerate(data))
            if op == 0x8:
                raise ConnectionError("browser closed the connection")
            if op == 0x9:
                self.send(data, opcode=0xA)
                continue
            if op in (0x1, 0x2, 0x0):
                parts.append(data)
                if b0 & 0x80:
                    return b"".join(parts).decode("utf-8", "replace")


class Browser:
    def __init__(self, url, approve_timeout=120):
        self.ws = WebSocket(url, timeout=approve_timeout)
        self.ws.sock.settimeout(30)
        self.next_id = 0
        self.on_event = None    # callable(message) for events (e.g. screencast frames to acknowledge)

    def call(self, method, params=None, session=None):
        self.next_id += 1
        my_id = self.next_id   # notify() may send more commands while we wait for this answer
        msg = {"id": my_id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == my_id:
                if "error" in r:
                    raise RuntimeError(f"{method}: {r['error'].get('message')}")
                return r.get("result", {})
            if "method" in r and self.on_event:
                self.on_event(r)

    def notify(self, method, params=None, session=None):
        """Send a command without waiting for its result (used to acknowledge events)."""
        self.next_id += 1
        msg = {"id": self.next_id, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))

    def pages(self):
        return [t for t in self.call("Target.getTargets")["targetInfos"] if t.get("type") == "page"]

    def attach(self, target_id):
        return self.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})["sessionId"]

    def evaluate(self, session, expression):
        r = self.call("Runtime.evaluate", {"expression": expression, "returnByValue": True,
                                           "awaitPromise": False}, session)
        if "exceptionDetails" in r:
            raise RuntimeError(r["exceptionDetails"].get("text", "evaluation failed"))
        return r.get("result", {}).get("value")


def connect(target="main", approve_timeout=120):
    return Browser(browser_ws_url(target), approve_timeout)
