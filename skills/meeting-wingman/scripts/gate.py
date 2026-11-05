#!/usr/bin/env python3
"""meeting-wingman gate: decides which transcript lines are worth waking Claude for.

Reads transcript lines ("[HH:MM:SS] text", translations as "[HH:MM:SS] ↳ xx: text") on stdin.
A line that matches a trigger for the current mode is printed at once as an event, with the quiet
lines since the previous event as context (up to 8). Everything else is held and printed as one digest every few minutes,
so Claude keeps up with the meeting without a reply for every sentence.

    tail -F transcript.txt | gate.py --mode coach|team|both [--names "Ana, Ana Silva"] [--digest 300]
    gate.py --raw          # pass every line through, no filtering

Triggers by mode (all modes also wake on "wingman", however the captions spell it):
  coach   question, name, number      (what the user may have to answer or correct)
  team    action, decision, blocker, name, date
  both    all of the above

Standard library only.
"""
import argparse
import os
import re
import select
import sys
import time
import unicodedata


def fold(s):
    s = unicodedata.normalize("NFKD", s.casefold().replace("ı", "i"))
    return "".join(c for c in s if not unicodedata.combining(c))


def rx(*parts):
    return re.compile(r"(?:%s)" % "|".join(parts))


W = r"(?:^|(?<=[\s,;:(\"'«-]))"   # word start
E = r"(?=$|[\s,.;:!?)\"'»-])"     # word end

QUESTION = rx(
    r"\?",
    # English: an auxiliary opening the sentence, or a wh-word followed by one ("when will", "how do").
    # A bare wh-word is not enough: "When the link comes back, it syncs" is a statement.
    r"(?:^|[.!]\s+)(?:can|could|would|will|do|does|did|is|are|was|were|should|shall)\s+(?:you|we|i|it|they|he|she|this|that|there|anyone|somebody)\b",
    r"\b(?:what|why|how|when|where|who|which)\s+(?:is|are|was|were|do|does|did|can|could|would|will|should|has|have|about|if|else|exactly|much|many|long|often|soon)\b",
    r"\b(?:any questions|do you|did you|can you|could you|would you|are you|have you|what about|how about)\b",
    # Turkish: question particle and question words
    W + r"m[iu](?:s[iu]n(?:[iu]z)?|y[iu]z|d[iu]r|yd[iu]|s[iu]n)?" + E,
    W + r"(?:neden|niye|nicin|nasil|kim|kimin|hangi|kac|nerede|nereden|nereye|ne zaman|acaba)" + E,
    # German, French, Spanish, Italian, Dutch, Portuguese
    r"\b(?:warum|wieso|weshalb|wann|welche[rsmn]?|konnen sie|konnten sie)\b",
    r"\b(?:pourquoi|comment|quand|est-ce que)\b",
    r"\b(?:por que|como|cuando|donde|quien|cual)\b",
    r"\b(?:perche|quando|dove|quale)\b",
    r"\b(?:waarom|wanneer|hoe|welke)\b",
    r"\b(?:por que|quando|onde|qual)\b",
)
ACTION = rx(
    r"\b(?:i'll|i will|i can take|i'll take|let me|i'm on it|i can do|can you|could you|would you mind|please|let's|action item|follow up|follow-up|take care of|assign|owner|to-?do)\b",
    W + r"(?:yaparim|hallederim|bakarim|gonderirim|hazirlarim|ayarlarim|ilgilenirim|alirim|yazarim|ararim|kontrol ederim|ben alayim|ben bakayim|uzerime|ustume)" + E,
    W + r"\w*(?:ar|er|ir|ur)\s+m[iu]s[iu]n(?:[iu]z)?" + E,      # yapar misin, bakar misiniz
    W + r"(?:yapalim|edelim|bakalim|gonderelim|konusalim|toplanalim|aksiyon|gorev|takip)" + E,
    r"\b(?:ich mache|ich kummere mich|kannst du|konnen sie|je m'en occupe|peux-tu|pouvez-vous|yo me encargo|puedes)\b",
)
DATE = rx(
    r"\b(?:by|until|before|on|next|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|tomorrow|week|month|eod|eow)\b",
    r"\b(?:tomorrow|end of (?:the )?(?:day|week|month)|next week|deadline|due)\b",
    W + r"(?:yarin|haftaya|hafta sonu|gun sonu|ay sonu)\w*" + E,
    W + r"(?:pazartesi|sali|carsamba|persembe|cuma|cumartesi|pazar)(?:ya|a|ye|e)?\s+kadar" + E,
    r"\b\d{1,2}[./]\d{1,2}(?:[./]\d{2,4})?\b",
)
DECISION = rx(
    r"\b(?:we decided|decided|let's go with|we'll go with|agreed|approved|final decision|sign(?:ed)? off)\b",
    W + r"(?:karar|anlastik|onaylandi|boyle yapalim|oyle yapalim|tamam o zaman)" + E,
    r"\b(?:entschieden|beschlossen|decide|decidimos|acordamos)\b",
)
BLOCKER = rx(
    r"\b(?:blocked|blocker|blocking|stuck|waiting on|waiting for|issue|bug|broken|delay(?:ed)?|risk)\b",
    W + r"(?:bloklu|takildi|takili|bekliyoruz|sorun|problem|hata|gecik\w*|risk)" + E,
)
# The assistant itself, as captions spell it ("wingman", "vingman", "vincman", "ringman", "winkman"...).
WAKE = re.compile(r"\b(?:w|v|r)(?:i|e)n(?:g|k|c)?(?:h)?\s?m(?:a|e)n\b|\bregmen\b|\bmeeting[- ]?wingman\b")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|percent|yuzde|€|\$|£|tl|lira|euro|eur|dolar|dollars?|usd|million|milyon|milyar|billion|bin|thousand|k\b|m\b)|\b\d{2,}\b|yuzde\s*\d")

MODES = {
    "coach": ("wingman", "question", "name", "number"),
    "team": ("wingman", "action", "decision", "blocker", "date", "name"),
}
MODES["both"] = tuple(dict.fromkeys(MODES["coach"] + MODES["team"]))

LINE = re.compile(r"^\[(\d\d:\d\d:\d\d)\]\s?(.*)$")
TRANSLATION = re.compile(r"^\u21b3\s?\w[\w-]*:\s")


SELF_LABELS = {"you", "siz", "sen", "du", "sie", "vous", "tu", "tú", "usted", "voce", "você", "jij", "u", "ty", "ви", "вы"}


def split_speaker(text):
    """Captions lines look like "Ana Silva: text". Returns (speaker, text)."""
    m = re.match(r"^([^:\n]{1,40}):\s(.*)$", text)
    return (m.group(1).strip(), m.group(2)) if m else ("", text)


def classify(text, names=(), mode="both", speaker="", is_self=False):
    """Return the triggers that `text` hits, in a stable order, limited to `mode`.

    When the user is the speaker, their own questions and their own name do not wake Claude in
    coach mode; numbers still do, so a wrong figure can be corrected."""
    t = fold(text)
    hits = []
    checks = {
        "question": lambda: QUESTION.search(t),
        "action": lambda: ACTION.search(t),
        "decision": lambda: DECISION.search(t),
        "blocker": lambda: BLOCKER.search(t),
        "date": lambda: DATE.search(t),
        "number": lambda: NUMBER.search(t),
        "wingman": lambda: WAKE.search(t),
        "name": lambda: any(re.search(r"\b%s\b" % re.escape(n), t) for n in names),
    }
    skip = {"question", "name"} if is_self else set()
    for k in MODES[mode]:
        if k not in skip and checks[k]():
            hits.append(k)
    return hits


class Gate:
    def __init__(self, out, mode="both", names=(), digest=300, context=8, clock=time.time, speakers=False):
        self.out, self.mode, self.digest, self.context, self.clock = out, mode, digest, context, clock
        self.speakers = speakers
        self.names = [fold(n).strip() for n in names if n.strip()]
        self.held = []         # lines since the last event, for the digest
        self.last_emit = clock()
        self.pending = None    # [stamp, text, [translation lines]]

    def feed(self, raw):
        raw = raw.rstrip("\n")
        m = LINE.match(raw)
        if not m:
            return
        stamp, text = m.groups()
        if TRANSLATION.match(text) and self.pending and self.pending[0] == stamp:
            self.pending[2].append(raw)
            return
        self.settle()
        self.pending = [stamp, text, [raw]]

    def settle(self):
        """Process the pending line once its translation (if any) has arrived."""
        if not self.pending:
            return
        stamp, text, lines = self.pending
        self.pending = None
        speaker, body = split_speaker(text) if self.speakers else ("", text)
        is_self = bool(speaker) and (fold(speaker) in SELF_LABELS or fold(speaker) in self.names)
        hits = classify(body, self.names, self.mode, speaker, is_self)
        if hits:
            self.emit(stamp, hits, lines)
        else:
            self.held.append(lines)

    def emit(self, stamp, hits, lines):
        """Print a trigger with the quiet lines since the last event as context (none twice)."""
        w = self.out.write
        w(f"\u25b6 {', '.join(hits)} \u00b7 {stamp}\n")
        ctx = self.held[-self.context:]
        if len(self.held) > len(ctx):
            w(f"  ({len(self.held) - len(ctx)} earlier lines since the last event: wingman show)\n")
        for group in ctx:
            for l in group:
                w(f"  \u2026 {l}\n")
        for l in lines:
            w(f"  {l}\n")
        self.out.flush()
        self.held = []
        self.last_emit = self.clock()

    def tick(self):
        if self.held and self.clock() - self.last_emit >= self.digest:
            self.flush_digest()

    def flush_digest(self):
        if not self.held:
            return
        first = LINE.match(self.held[0][0]).group(1)
        last = LINE.match(self.held[-1][0]).group(1)
        n = len(self.held)
        w = self.out.write
        w(f"\u25c7 digest {first}\u2013{last} \u00b7 {n} line{'s' if n != 1 else ''}, no trigger\n")
        shown = self.held[-40:]
        if n > len(shown):
            w(f"  ({n - len(shown)} earlier lines: wingman show)\n")
        for group in shown:
            for l in group:
                w(f"  {l}\n")
        self.out.flush()
        self.held = []
        self.last_emit = self.clock()


def main():
    ap = argparse.ArgumentParser(description="Filter a live transcript into events for Claude.")
    ap.add_argument("--mode", choices=sorted(MODES), default="both")
    ap.add_argument("--names", default="", help="comma-separated names of the user (and aliases)")
    ap.add_argument("--digest", type=float, default=300, help="seconds between digests of quiet lines")
    ap.add_argument("--raw", action="store_true", help="pass every line through unfiltered")
    ap.add_argument("--speakers", action="store_true", help='lines carry a "Speaker: " prefix (captions)')
    a = ap.parse_args()
    if a.raw:
        for line in sys.stdin:
            sys.stdout.write(line)
            sys.stdout.flush()
        return
    g = Gate(sys.stdout, a.mode, a.names.split(","), a.digest, speakers=a.speakers)
    # Read the raw descriptor: select() on a buffered stream misses lines already in its buffer.
    fd, buf = sys.stdin.fileno(), b""
    while True:
        ready, _, _ = select.select([fd], [], [], 0.5)
        if ready:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            buf += chunk
            *lines, buf = buf.split(b"\n")
            for line in lines:
                g.feed(line.decode("utf-8", "replace"))
        else:
            g.settle()           # no translation followed within 0.5 s
            g.tick()
    g.settle()
    g.flush_digest()


if __name__ == "__main__":
    main()
