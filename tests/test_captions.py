import os
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

import _path  # noqa: F401
from captions import Tracker


class TrackerTest(unittest.TestCase):
    def setUp(self):
        self.now = [100.0]
        self.t = Tracker(stable=1.5, long=60, clock=lambda: self.now[0])

    def step(self, blocks, dt=0.5):
        out = self.t.update(blocks)
        self.now[0] += dt
        return [(s, x) for _, s, x in out]

    def test_growing_text_is_emitted_once_when_stable(self):
        b = lambda x: [{"id": "1", "speaker": "Ana", "text": x}]
        self.assertEqual(self.step(b("Good")), [])
        self.assertEqual(self.step(b("Good morning")), [])
        self.assertEqual(self.step(b("Good morning all")), [])
        out = []
        for _ in range(5):
            out += self.step(b("Good morning all"))
        self.assertEqual(out, [("Ana", "Good morning all")])

    def test_newer_block_finishes_the_older_one(self):
        self.step([{"id": "1", "speaker": "Ana", "text": "Hello there"}])
        out = self.step([{"id": "1", "speaker": "Ana", "text": "Hello there"},
                         {"id": "2", "speaker": "You", "text": "Hi"}])
        self.assertEqual(out, [("Ana", "Hello there")])

    def test_vanishing_block_is_not_lost(self):
        self.step([{"id": "1", "speaker": "Ana", "text": "Bye now"}])
        self.assertEqual(self.step([]), [("Ana", "Bye now")])

    def test_long_monologue_comes_in_sentences(self):
        text = "First sentence is here and it is long enough. Second one keeps going on and on"
        out = self.step([{"id": "1", "speaker": "Ana", "text": text}])
        self.assertEqual(out, [("Ana", "First sentence is here and it is long enough.")])

    def test_correction_before_emit(self):
        self.step([{"id": "1", "speaker": "Ana", "text": "let's starts"}])
        out = []
        for _ in range(5):
            out += self.step([{"id": "1", "speaker": "Ana", "text": "let's start"}])
        self.assertEqual(out, [("Ana", "let's start")])


def chrome():
    return next((c for c in ("google-chrome", "chromium", "chromium-browser") if shutil.which(c)), None)


@unittest.skipUnless(chrome(), "no Chrome/Chromium on this machine")
class MockMeetInBrowser(unittest.TestCase):
    """End to end: headless Chrome shows tests/fixtures/meet-mock.html, captions.py reads it."""

    def test_reads_mock_meet(self):
        import json
        import urllib.request
        import cdp
        here = os.path.dirname(os.path.abspath(__file__))
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        prof = tempfile.mkdtemp()
        page = "file://" + os.path.join(here, "fixtures", "meet-mock.html")
        br = subprocess.Popen([chrome(), "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={prof}",
                               "--no-first-run", "--no-sandbox", "--disable-gpu", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out, log = os.path.join(prof, "t.txt"), os.path.join(prof, "captions.log")
        cap = None
        try:
            for _ in range(60):     # wait until the debugging port answers
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1).read()
                    break
                except OSError:
                    time.sleep(0.5)
            env = dict(os.environ, WINGMAN_CAPTION_URL="meet-mock")
            cap = subprocess.Popen(["python3", os.path.join(_path.SCRIPTS, "captions.py"), out, "--cdp", str(port),
                                    "--interval", "0.4"], env=env, stdout=open(log, "w"), stderr=subprocess.STDOUT)
            time.sleep(2)
            # open the mock meeting only now, so the reader sees it from the first caption
            b = cdp.connect(str(port))
            tab = b.pages()[0]
            b.call("Page.navigate", {"url": page}, b.attach(tab["targetId"]))
            for _ in range(40):
                time.sleep(0.5)
                if os.path.exists(out) and "Nothing was lost." in open(out).read():
                    break
            time.sleep(1)
        finally:
            if cap:
                cap.terminate()
            br.terminate()
        text = open(out).read() if os.path.exists(out) else ""
        msg = "captions.py log:\n" + (open(log).read() if os.path.exists(log) else "(none)") + "\ntranscript:\n" + text
        self.assertIn("Maria: Good morning everyone, let's start with the pilot results.", text, msg)
        self.assertIn("You: What happens to the data when a site goes offline?", text, msg)
        self.assertIn("Nothing was lost.", text, msg)
        self.assertEqual(text.count("Good morning everyone"), 1, msg)


if __name__ == "__main__":
    unittest.main()
