#!/usr/bin/env python3
"""meeting-wingman segmenter: cuts live audio into utterances at pauses, not at fixed times.

Reads raw 16 kHz mono signed 16-bit PCM on stdin (from ffmpeg) and writes one WAV file per
utterance into OUTDIR, named HHMMSS.wav after the time speech started. A file is written under a
temporary name and renamed when complete, so a reader never sees a half-written chunk. Silence is
never written, which also keeps Whisper from inventing sentences.

    ffmpeg ... -f s16le -ac 1 -ar 16000 - | segmenter.py OUTDIR

Standard library only. Tunables (environment):

  WINGMAN_MAX_CHUNK   longest utterance in seconds before a forced cut   (default 15)
  WINGMAN_PAUSE       pause in seconds that ends an utterance            (default 0.7)
  WINGMAN_MIN_SPEECH  shorter bursts are dropped (coughs, clicks)        (default 0.6)
"""
import array
import math
import os
import signal
import sys
import time
import wave

RATE = 16000
FRAME = 480                      # 30 ms
FRAME_BYTES = FRAME * 2
MAX_CHUNK = float(os.environ.get("WINGMAN_MAX_CHUNK", "15"))
PAUSE = float(os.environ.get("WINGMAN_PAUSE", "0.7"))
MIN_SPEECH = float(os.environ.get("WINGMAN_MIN_SPEECH", "0.6"))
PREROLL = 0.3                    # keep a little audio before speech starts
ABS_FLOOR_DB = -50.0             # below this is silence whatever the noise floor says


def frame_db(buf):
    a = array.array("h", buf)
    if sys.byteorder == "big":
        a.byteswap()
    if not a:
        return -100.0
    ms = sum(x * x for x in a) / len(a)
    return 10 * math.log10(ms / (32768.0 ** 2)) if ms > 0 else -100.0


class Segmenter:
    """Energy-based voice activity detection with an adaptive noise floor."""

    def __init__(self, outdir, clock=time.time):
        self.outdir = outdir
        self.clock = clock
        self.noise_db = -60.0
        self.pre = []                # recent silent frames, for the pre-roll
        self.cur = []                # frames of the current utterance
        self.speech_frames = 0
        self.silent_run = 0
        self.start_ts = None
        self.written = []

    def threshold(self):
        return max(self.noise_db + 12.0, ABS_FLOOR_DB)

    def feed(self, buf):
        db = frame_db(buf)
        speech = db > self.threshold()
        if not speech:   # slowly track the background level while nobody speaks
            self.noise_db = 0.98 * self.noise_db + 0.02 * max(db, -90.0)
        if not self.cur:
            if speech:
                self.start_ts = self.clock() - len(self.pre) * FRAME / RATE
                self.cur = self.pre + [buf]
                self.pre = []
                self.speech_frames, self.silent_run = 1, 0
            else:
                self.pre.append(buf)
                self.pre = self.pre[-int(PREROLL * RATE / FRAME):]
            return
        self.cur.append(buf)
        if speech:
            self.speech_frames += 1
            self.silent_run = 0
        else:
            self.silent_run += 1
        dur = len(self.cur) * FRAME / RATE
        if self.silent_run * FRAME / RATE >= PAUSE or dur >= MAX_CHUNK:
            self.flush()

    def flush(self):
        if self.cur and self.speech_frames * FRAME / RATE >= MIN_SPEECH:
            self.write(b"".join(self.cur))
        self.cur, self.speech_frames, self.silent_run = [], 0, 0

    def write(self, pcm):
        name = time.strftime("%H%M%S", time.localtime(self.start_ts))
        path = os.path.join(self.outdir, name + ".wav")
        n = 1
        while os.path.exists(path):          # two utterances starting in the same second
            path = os.path.join(self.outdir, f"{name}_{n}.wav")
            n += 1
        tmp = path + ".part"
        with wave.open(tmp, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(RATE)
            w.writeframes(pcm)
        os.replace(tmp, path)
        self.written.append(path)


def _interrupt(*_):
    raise KeyboardInterrupt


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: segmenter.py OUTDIR  (raw s16le 16 kHz mono on stdin)")
    os.makedirs(sys.argv[1], exist_ok=True)
    seg = Segmenter(sys.argv[1])
    # On `wingman stop` (SIGTERM) write the utterance in progress instead of losing it.
    signal.signal(signal.SIGTERM, _interrupt)
    src = sys.stdin.buffer
    try:
        while True:
            buf = src.read(FRAME_BYTES)
            if len(buf) < FRAME_BYTES:
                break
            seg.feed(buf)
    except KeyboardInterrupt:
        pass
    seg.flush()


if __name__ == "__main__":
    main()
