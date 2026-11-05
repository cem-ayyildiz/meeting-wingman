import array
import math
import os
import tempfile
import unittest
import wave

import _path  # noqa: F401
from segmenter import FRAME, RATE, Segmenter


def tone(seconds, amp):
    n = int(seconds * RATE)
    return array.array("h", (int(amp * math.sin(2 * math.pi * 220 * i / RATE)) for i in range(n))).tobytes()


def silence(seconds, amp=30):   # a little noise, like a real line
    n = int(seconds * RATE)
    return array.array("h", ((amp if i % 2 else -amp) for i in range(n))).tobytes()


class SegmenterTest(unittest.TestCase):
    def feed(self, pcm, **env):
        d = tempfile.mkdtemp()
        t = [1_700_000_000.0]
        seg = Segmenter(d, clock=lambda: t[0])
        for i in range(0, len(pcm) - FRAME * 2 + 1, FRAME * 2):
            seg.feed(pcm[i:i + FRAME * 2])
            t[0] += FRAME / RATE
        seg.flush()
        return seg.written

    def durations(self, files):
        out = []
        for f in files:
            with wave.open(f) as w:
                out.append(w.getnframes() / RATE)
        return out

    def test_cuts_at_pauses(self):
        pcm = silence(1) + tone(2, 8000) + silence(1.2) + tone(1.5, 8000) + silence(1)
        files = self.feed(pcm)
        self.assertEqual(len(files), 2)
        for d, want in zip(self.durations(files), (2, 1.5)):
            self.assertTrue(want <= d <= want + 1.1, d)

    def test_silence_writes_nothing(self):
        self.assertEqual(self.feed(silence(5)), [])

    def test_short_click_is_dropped(self):
        self.assertEqual(self.feed(silence(1) + tone(0.2, 8000) + silence(1)), [])

    def test_long_speech_is_cut(self):
        files = self.feed(tone(32, 8000) + silence(1))
        self.assertGreaterEqual(len(files), 3)
        self.assertTrue(all(d <= 15.1 for d in self.durations(files)))

    def test_files_are_complete_and_named(self):
        files = self.feed(silence(0.5) + tone(1, 8000) + silence(1))
        self.assertEqual(len(files), 1)
        self.assertRegex(os.path.basename(files[0]), r"^\d{6}\.wav$")
        self.assertFalse(any(f.endswith(".part") for f in os.listdir(os.path.dirname(files[0]))))


if __name__ == "__main__":
    unittest.main()
