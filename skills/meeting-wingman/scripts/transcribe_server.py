#!/usr/bin/env python3
"""meeting-wingman transcriber: turns short WAV chunks into timestamped transcript lines.

Watches a directory for chunks named HHMMSS.wav, transcribes each with faster-whisper,
appends "[HH:MM:SS] text" to transcript.txt and deletes the chunk. The same script runs
locally (started by `wingman start`) or on a remote GPU host (copied there on every start).

Settings come from environment variables:

  WINGMAN_DIR        working directory                    (default: current directory)
  WINGMAN_IN         where chunks arrive                  (default: $WINGMAN_DIR/in)
  WINGMAN_LANG       language code (tr, en, de ...) or empty for auto-detect
  WINGMAN_MODEL      faster-whisper model                 (default: large-v3 on GPU, small on CPU)
  WINGMAN_DEVICE     cuda | cpu | auto                    (default: auto)
  WINGMAN_SKIP_LAST  1 = ignore the newest chunk (it is still being written; needed when
                     the server reads the capture directory directly, i.e. local mode)

Recognition hints (names, acronyms) are read from $WINGMAN_DIR/terms.txt, comma separated.
"""
import glob
import os
import re
import time
import unicodedata

from faster_whisper import WhisperModel

BASE = os.path.abspath(os.path.expanduser(os.environ.get("WINGMAN_DIR", ".")))
IN = os.path.expanduser(os.environ.get("WINGMAN_IN", os.path.join(BASE, "in")))
OUT = os.path.join(BASE, "transcript.txt")
LANG = os.environ.get("WINGMAN_LANG", "") or None
SKIP_LAST = os.environ.get("WINGMAN_SKIP_LAST") == "1"
os.makedirs(IN, exist_ok=True)


def pick_device():
    dev = os.environ.get("WINGMAN_DEVICE", "auto")
    if dev != "auto":
        return dev
    try:
        import ctranslate2
        return "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    except Exception:
        return "cpu"


DEVICE = pick_device()
MODEL = os.environ.get("WINGMAN_MODEL") or ("large-v3" if DEVICE == "cuda" else "small")

TERMS = ""
_tf = os.path.join(BASE, "terms.txt")
if os.path.exists(_tf):
    TERMS = open(_tf, encoding="utf-8").read().strip()


def fold(s):
    """Case- and accent-insensitive form. Handles Turkish: 'İ'.lower() gives i + combining dot,
    and 'ı' has no decomposition, so both are mapped to plain i."""
    s = unicodedata.normalize("NFKD", s.casefold().replace("ı", "i"))
    return "".join(c for c in s if not unicodedata.combining(c))


# Phrases Whisper tends to invent on silence or music (in fold() form). Add your language's.
HALLUCINATIONS = (
    # English
    "thank you for watching", "thanks for watching", "please subscribe", "subtitles by",
    # Turkish
    "altyazi m.k", "izlediginiz icin tesekkur", "abone olmayi unutmayin", "altyazi",
    "tesekkurler", "sesli betimleme",
    # German / French / Spanish (Amara.org credits)
    "untertitel der amara.org", "untertitelung", "sous-titres realises par",
    "subtitulos realizados por", "amara.org",
)
TERM_SET = {fold(t).strip(" .") for t in TERMS.split(",") if t.strip()}


def is_hallucination(text):
    m = fold(text).strip(" .!")
    if len(m) < 3:
        return True
    if any(m.startswith(h) and len(m) < len(h) + 15 for h in HALLUCINATIONS):
        return True
    # On silence the model sometimes reads the hint list back: "ACME, ML-KEM, O-RAN, ..."
    parts = [p.strip(" .") for p in m.split(",") if p.strip(" .")]
    if TERM_SET and len(parts) >= 3 and sum(p in TERM_SET for p in parts) >= 0.7 * len(parts):
        return True
    return False


model = WhisperModel(MODEL, device=DEVICE,
                     compute_type="float16" if DEVICE == "cuda" else "int8")
print(f"model ready ({MODEL}, {DEVICE}, language={LANG or 'auto'})", flush=True)

previous = ""
while True:
    chunks = sorted(glob.glob(os.path.join(IN, "*.wav")))  # name = start time, sorts correctly
    if SKIP_LAST:
        chunks = chunks[:-1]
    if not chunks:
        time.sleep(0.5)
        continue
    for f in chunks:
        name = os.path.basename(f)[:-4]
        stamp = f"{name[0:2]}:{name[2:4]}:{name[4:6]}" if re.fullmatch(r"\d{6}", name) else name
        try:
            # condition_on_previous_text=False: with it on, muffled audio made the model repeat
            # the previous sentence for minutes.
            segs, _ = model.transcribe(f, language=LANG, beam_size=5 if DEVICE == "cuda" else 1,
                                       vad_filter=True, initial_prompt=TERMS or None,
                                       condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segs
                            if s.no_speech_prob < 0.6 and not is_hallucination(s.text)).strip()
        except Exception as e:  # broken chunk: drop it, keep going
            print(f"{name}: {e}", flush=True)
            text = ""
        if text and text != previous:
            with open(OUT, "a", encoding="utf-8") as o:
                o.write(f"[{stamp}] {text}\n")
            previous = text
        os.remove(f)
