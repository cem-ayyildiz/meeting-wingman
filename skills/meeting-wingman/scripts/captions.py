#!/usr/bin/env python3
"""meeting-wingman captions: reads the meeting's own live captions from the browser, with speaker names.

Connects to Chrome, Edge or Chromium over the DevTools protocol, finds the Google Meet, Microsoft
Teams or Zoom tab, and reads the captions the meeting shows (turn them on in the meeting). No
audio is recorded and no GPU is needed. Each finished caption becomes a transcript line
"[HH:MM:SS] Speaker: text", in the same file format as the audio pipeline.

    captions.py OUT.txt [--cdp main|PORT] [--platform auto|meet|teams|zoom] [--translate LANG]

  --cdp main   the user's own browser (Chrome asks "Allow remote debugging?" once). Needs remote
               debugging turned on at chrome://inspect/#remote-debugging
  --cdp PORT   a browser started with --remote-debugging-port=PORT

Custom DOM selectors, if a platform changes its page: WINGMAN_CAPTION_BLOCK (one caption block),
WINGMAN_CAPTION_SPEAKER and WINGMAN_CAPTION_TEXT (inside a block). WINGMAN_CAPTION_URL: a regex that
picks the tab by URL, for a meeting site not in the list.
"""
import argparse
import json
import os
import re
import sys
import time

import cdp

PLATFORMS = {
    "meet": re.compile(r"^https://meet\.google\.com/[a-z]{3,4}-[a-z]{3,4}-[a-z]{3,4}"),
    "teams": re.compile(r"^https://(?:teams\.microsoft\.com|teams\.live\.com|teams\.cloud\.microsoft)/"),
    "zoom": re.compile(r"^https://(?:[\w-]+\.)?zoom\.us/wc/|^https://app\.zoom\.us/wc/"),
}

# Runs in the page. Returns {"found": bool, "blocks": [{"id", "speaker", "text"}]}.
# Each caption block gets a stable data-wm-id so it can be followed across polls.
EXTRACT = r"""
(() => {
  const P = %(platform)s, C = %(custom)s;
  let n = window.__wmN || 0;
  const id = el => el.dataset.wmId || (el.dataset.wmId = String(window.__wmN = ++n));
  const txt = el => (el && (el.innerText || el.textContent) || "").replace(/\s+/g, " ").trim();
  const out = [];
  const add = (el, speaker, text) => { if (text) out.push({id: id(el), speaker: speaker || "", text}); };
  if (C.block) {
    document.querySelectorAll(C.block).forEach(b => add(b,
      C.speaker ? txt(b.querySelector(C.speaker)) : "", C.text ? txt(b.querySelector(C.text)) : txt(b)));
    return {found: out.length > 0 || !!document.querySelector(C.block), blocks: out};
  }
  if (P === "meet") {
    // The captions panel is a region whose label says "Captions" in the UI language.
    const label = /caption|altyaz|untertitel|sous-titre|subt[ií]tulo|sottotitol|ondertitel|legenda|napisy|субтитр|字幕|자막/i;
    const region = [...document.querySelectorAll('[role="region"][aria-label]')].find(r => label.test(r.getAttribute("aria-label")));
    if (!region) return {found: false, blocks: []};
    // A block holds the speaker's avatar, name and text. Climb from each avatar to the first
    // element that shows two lines (name + text), never into one that holds a second avatar.
    // A block with no text yet is skipped until its text appears.
    const lines2 = el => (el.innerText || "").split("\n").filter(s => s.trim()).length >= 2;
    const imgs = [...region.querySelectorAll("img")];
    const blocks = [];
    for (const img of imgs) {
      let b = img.parentElement;
      while (b && b !== region && !lines2(b) && b.parentElement !== region &&
             b.parentElement.querySelectorAll("img").length === 1) b = b.parentElement;
      if (b && b !== region && lines2(b) && b.querySelectorAll("img").length === 1 && !blocks.includes(b)) blocks.push(b);
    }
    if (!blocks.length && !imgs.length) { add(region, "", txt(region)); return {found: true, blocks: out}; }
    for (const b of blocks) {
      const lines = (b.innerText || "").split("\n").map(s => s.trim()).filter(Boolean);
      if (lines.length >= 2) add(b, lines[0], lines.slice(1).join(" "));
      else add(b, "", lines.join(" "));
    }
    return {found: true, blocks: out};
  }
  if (P === "teams") {
    const items = document.querySelectorAll('[data-tid="closed-caption-message"], [data-tid="closed-captions-renderer"] [data-tid="closed-caption-text"]');
    if (!items.length) return {found: !!document.querySelector('[data-tid="closed-captions-renderer"], [data-tid="closed-caption-v2-window-wrapper"]'), blocks: []};
    const seen = new Set();
    for (const it of items) {
      const b = it.closest('[data-tid="closed-caption-message"]') || it.closest('.fui-ChatMessageCompact') || it.parentElement;
      if (seen.has(b)) continue; seen.add(b);
      add(b, txt(b.querySelector('[data-tid="author"]')), txt(b.querySelector('[data-tid="closed-caption-text"]')) || txt(b));
    }
    return {found: true, blocks: out};
  }
  if (P === "zoom") {
    // Prefer the full transcript panel (it has names); fall back to the subtitle overlay.
    const panel = document.querySelectorAll(".lt-full-transcript__item");
    if (panel.length) {
      panel.forEach(b => add(b, txt(b.querySelector(".lt-full-transcript__display-name")),
                                txt(b.querySelector(".lt-full-transcript__message")) || txt(b)));
      return {found: true, blocks: out};
    }
    const subs = document.querySelectorAll(".live-transcription-subtitle__item");
    subs.forEach(b => add(b, "", txt(b)));
    return {found: subs.length > 0 || !!document.querySelector("#live-transcription-subtitle"), blocks: out};
  }
  return {found: false, blocks: []};
})()
"""


class Tracker:
    """Turns caption blocks that grow and get rewritten in place into finished lines.

    A block's new text is emitted when it has not changed for `stable` seconds, when a newer block
    appears after it, when it disappears, or in sentence-sized pieces when it runs long."""

    def __init__(self, stable=1.5, long=220, clock=time.time):
        self.stable, self.long, self.clock = stable, long, clock
        self.blocks = {}     # id -> {speaker, text, changed, done, first}
        self.order = []

    def update(self, blocks):
        now, out = self.clock(), []
        ids = [b["id"] for b in blocks]
        for b in blocks:
            s = self.blocks.get(b["id"])
            if s is None:
                s = self.blocks[b["id"]] = {"speaker": b["speaker"], "text": "", "changed": now, "done": 0, "first": now}
                self.order.append(b["id"])
            if b["text"] != s["text"]:
                if s["done"] >= len(s["text"]):      # nothing pending yet: the new text starts now
                    s["first"] = now
                s["text"], s["changed"] = b["text"], now
                s["speaker"] = b["speaker"] or s["speaker"]
        for i, bid in enumerate(self.order):
            s = self.blocks[bid]
            pending = s["text"][s["done"]:].strip() if len(s["text"]) > s["done"] else ""
            if not pending:
                continue
            gone = bid not in ids
            newer = any(o in ids for o in self.order[i + 1:])
            if gone or newer or now - s["changed"] >= self.stable:
                out.append(self.take(s, len(s["text"])))
            elif len(pending) >= self.long:
                cut = max(s["text"].rfind(p, s["done"]) for p in (". ", "? ", "! "))
                if cut > s["done"]:
                    out.append(self.take(s, cut + 1))
        # forget blocks that left the page and are fully emitted
        for bid in [b for b in self.order if b not in ids and self.blocks[b]["done"] >= len(self.blocks[b]["text"])]:
            self.order.remove(bid)
            del self.blocks[bid]
        return out

    def take(self, s, end):
        text = s["text"][s["done"]:end].strip()
        s["done"] = end
        stamp = time.strftime("%H:%M:%S", time.localtime(s["first"]))
        s["first"] = self.clock()
        return stamp, s["speaker"], text


def find_tab(browser, platform):
    custom = os.environ.get("WINGMAN_CAPTION_URL")    # regex for another meeting site, or for tests
    for p in browser.pages():
        if custom and re.search(custom, p.get("url", "")):
            return (platform if platform != "auto" else "meet"), p
        for name, rx in PLATFORMS.items():
            if (platform in ("auto", name)) and rx.match(p.get("url", "")):
                return name, p
    return None, None


def main():
    ap = argparse.ArgumentParser(description="Read live captions from a Meet, Teams or Zoom tab.")
    ap.add_argument("out")
    ap.add_argument("--cdp", default=os.environ.get("WINGMAN_CDP", "main"))
    ap.add_argument("--platform", default="auto", choices=["auto", *PLATFORMS])
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--translate", default=os.environ.get("WINGMAN_TRANSLATE", ""))
    a = ap.parse_args()

    print(f"connecting to the browser ({a.cdp}); approve 'Allow remote debugging' if the browser asks", flush=True)
    browser = cdp.connect(a.cdp)
    translate = None
    if a.translate:
        from translate import Translator
        translate = Translator(a.translate)

    platform, tab, said = None, None, set()
    while tab is None:
        platform, tab = find_tab(browser, a.platform)
        if tab is None:
            if "wait" not in said:
                print("waiting for a Google Meet, Microsoft Teams or Zoom tab (web client) to open", flush=True)
                said.add("wait")
            time.sleep(3)
    session = browser.attach(tab["targetId"])
    custom = {k: os.environ.get(f"WINGMAN_CAPTION_{k.upper()}", "") for k in ("block", "speaker", "text")}
    expr = EXTRACT % {"platform": json.dumps(platform), "custom": json.dumps(custom)}
    print(f"captions ready ({platform}: {tab.get('title', '')[:60]}"
          + (f", translate to {translate.target} on {translate.device}" if translate else "") + ")", flush=True)

    tracker, found_before = Tracker(), None
    while True:
        try:
            r = browser.evaluate(session, expr) or {"found": False, "blocks": []}
        except (RuntimeError, ConnectionError) as e:
            print(f"lost the tab ({e}); waiting for it again", flush=True)
            time.sleep(3)
            platform, tab = find_tab(browser, a.platform)
            if tab:
                session = browser.attach(tab["targetId"])
            continue
        if r["found"] != found_before:
            print("captions visible" if r["found"] else
                  "no captions on the page: turn on captions (CC) in the meeting", flush=True)
            found_before = r["found"]
        lines = tracker.update(r["blocks"])
        if lines:
            with open(a.out, "a", encoding="utf-8") as f:
                for stamp, speaker, text in lines:
                    f.write(f"[{stamp}] {speaker + ': ' if speaker else ''}{text}\n")
                    if translate:
                        try:
                            t = translate(text, os.environ.get("WINGMAN_LANG") or "en")
                            if t:
                                f.write(f"[{stamp}] ↳ {translate.target}: {t}\n")
                        except Exception as e:
                            print(f"translation failed: {e}", flush=True)
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
