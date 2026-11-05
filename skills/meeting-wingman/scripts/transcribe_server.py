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
  WINGMAN_TRANSLATE  target language (de, tr, en ...): add a translated line under each line
  WINGMAN_SKIP_LAST  1 = ignore the newest chunk (it is still being written; needed when
                     the server reads the capture directory directly, i.e. local mode)

If the GPU cannot be used (no CUDA, out of memory), the model is loaded on the CPU instead.
Recognition hints (names, acronyms) are read from $WINGMAN_DIR/terms.txt, comma separated.
"""
import glob
import sys
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


def has_cuda():
    try:
        import ctranslate2
        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


WANT = os.environ.get("WINGMAN_DEVICE", "auto")

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


def load_model():
    """GPU first (large-v3), CPU (small) when CUDA is missing or the GPU is out of memory."""
    order = ["cuda", "cpu"] if (WANT == "cuda" or (WANT == "auto" and has_cuda())) else ["cpu"]
    for dev in order:
        name = os.environ.get("WINGMAN_MODEL") or ("large-v3" if dev == "cuda" else "small")
        if dev == "cpu" and len(order) > 1 and os.environ.get("WINGMAN_MODEL"):
            name = "small"   # a GPU-sized model would not keep up on the CPU
        try:
            m = WhisperModel(name, device=dev, compute_type="float16" if dev == "cuda" else "int8")
            return m, name, dev
        except Exception as e:
            print(f"whisper: {name} on {dev} failed: {e}", flush=True)
    raise SystemExit("whisper: no device worked")


model, MODEL, DEVICE = load_model()
translate = None
if os.environ.get("WINGMAN_TRANSLATE"):
    from translate import Translator
    translate = Translator(os.environ["WINGMAN_TRANSLATE"])
print(f"model ready ({MODEL}, {DEVICE}, language={LANG or 'auto'}"
      + (f", translate to {translate.target} with {translate.name} on {translate.device}" if translate else "")
      + ")", flush=True)

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
            segs, info = model.transcribe(f, language=LANG, beam_size=5 if DEVICE == "cuda" else 1,
                                       vad_filter=True, initial_prompt=TERMS or None,
                                       condition_on_previous_text=False)
            text = " ".join(s.text.strip() for s in segs
                            if s.no_speech_prob < 0.6 and not is_hallucination(s.text)).strip()
            spoken = LANG or info.language
        except Exception as e:  # broken chunk: drop it, keep going
            print(f"{name}: {e}", flush=True)
            text = ""
        if text and text != previous:
            line = f"[{stamp}] {text}\n"
            if translate:
                try:
                    t = translate(text, spoken)
                    if t:
                        line += f"[{stamp}] \u21b3 {translate.target}: {t}\n"
                except Exception as e:
                    print(f"{name}: translation failed: {e}", flush=True)
            with open(OUT, "a", encoding="utf-8") as o:
                o.write(line)
            previous = text
        os.remove(f)
