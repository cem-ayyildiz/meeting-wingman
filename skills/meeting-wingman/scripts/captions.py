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
  --meeting T  read the tab whose title or URL contains T (several meetings open)
  --list       list the meeting tabs that are open and exit

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
    # meet.google.com/abc-defg-hij, also with a path before the code (/meet/abc-defg-hij, /_meet/...)
    "meet": re.compile(r"^https://meet\.google\.com/(?:[\w-]+/)*[a-z]{3,4}-[a-z]{3,4}-[a-z]{3,4}(?:[/?#]|$)"),
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
  // Meetings can run inside same-origin iframes (the Zoom web client does): search those too.
  const D = [document, ...[...document.querySelectorAll("iframe")].map(f => { try { return f.contentDocument; } catch (e) { return null; } }).filter(Boolean)];
  const qa = s => D.flatMap(d => [...d.querySelectorAll(s)]);
  const q1 = s => { for (const d of D) { const e = d.querySelector(s); if (e) return e; } return null; };
  const out = [];
  const add = (el, speaker, text) => { if (text) out.push({id: id(el), speaker: speaker || "", text}); };
  if (C.block) {
    qa(C.block).forEach(b => add(b,
      C.speaker ? txt(b.querySelector(C.speaker)) : "", C.text ? txt(b.querySelector(C.text)) : txt(b)));
    return {found: out.length > 0 || !!q1(C.block), blocks: out};
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
    // New Teams (checked on teams.live.com, Nov 2026): one .fui-ChatMessageCompact per caption,
    // holding [data-tid=author] and [data-tid=closed-caption-text], inside a virtual list.
    const texts = document.querySelectorAll('[data-tid="closed-caption-text"]');
    const panel = document.querySelector('[data-tid="closed-caption-v2-window-wrapper"], [data-tid="closed-caption-renderer-wrapper"], [data-tid="closed-captions-v2-items-renderer"]');
    if (!texts.length) return {found: !!panel, blocks: []};
    const seen = new Set();
    for (const t of texts) {
      const b = t.closest('.fui-ChatMessageCompact') || t.closest('[data-tid="closed-caption-message"]') || t.parentElement;
      if (seen.has(b)) continue; seen.add(b);
      add(b, txt(b.querySelector('[data-tid="author"]')), txt(t));
    }
    return {found: true, blocks: out};
  }
  if (P === "zoom") {
    // Prefer the full transcript panel (it has names); fall back to the subtitle overlay.
    const panel = qa(".lt-full-transcript__item");
    if (panel.length) {
      panel.forEach(b => add(b, txt(b.querySelector(".lt-full-transcript__display-name")),
                                txt(b.querySelector(".lt-full-transcript__message")) || txt(b)));
      return {found: true, blocks: out};
    }
    // Checked on app.zoom.us/wc (Nov 2026): the subtitle overlay holds plain spans, no names.
    const subs = qa(".live-transcription-subtitle__item");
    subs.forEach(b => add(b, "", txt(b)));
    return {found: subs.length > 0 || !!q1(".live-transcription-subtitle__box, .lt-subtitle-wrap, #live-transcription-subtitle"), blocks: out};
  }
  return {found: false, blocks: []};
})()
"""


def fold(text):
    """Compare captions without case and punctuation: platforms re-punctuate a caption when it settles."""
    return re.sub(r"[\W_]+", "", text.casefold())


# Interface text that sits inside caption areas (Meet's "Jump to bottom" button, icon ligatures).
UI_NOISE = re.compile(r"^(?:arrow_\w+|keyboard_arrow_\w+|expand_\w+)?\s*"
                      r"(?:jump to bottom|scroll to bottom|en alta (?:git|in|atla)|nach unten springen|"
                      r"aller en bas|ir al final)?\s*$", re.I)


class Tracker:
    """Turns caption blocks that grow and get rewritten in place into finished lines.

    A block's new text is emitted when a newer block appears after it, when it disappears, when it
    has not changed for `stable` seconds (twice that when it does not end in punctuation, so a slow
    speaker's word is not split), or in sentence-sized pieces when it runs long. A line that repeats one just
    emitted (an interim caption followed by its punctuated final form) is dropped."""

    def __init__(self, stable=1.5, long=220, clock=time.time):
        self.stable, self.long, self.clock = stable, long, clock
        self.blocks = {}     # id -> {speaker, text, changed, done, first}
        self.order = []
        self.recent = []     # (speaker, folded text) of the last lines emitted

    def update(self, blocks):
        now, out = self.clock(), []
        ids = [b["id"] for b in blocks]
        for b in blocks:
            s = self.blocks.get(b["id"])
            if s is None:
                s = self.blocks[b["id"]] = {"speaker": b["speaker"], "text": "", "changed": now, "done": 0, "first": now}
                self.order.append(b["id"])
            # Platforms correct the last words of a caption in place; a different caption in the
            # same element (a virtual list reusing it) shares little or nothing with the old text.
            old, new = fold(s["text"]), fold(b["text"])
            common = len(os.path.commonprefix([old, new]))
            reused = bool(old) and (
                (b["speaker"] and s["speaker"] and b["speaker"] != s["speaker"]) or
                common < len(old) / 2)
            if reused:
                if len(s["text"]) > s["done"] and s["text"][s["done"]:].strip():
                    out.append(self.take(s, len(s["text"])))
                s.update(speaker=b["speaker"], text="", done=0, first=now, changed=now)
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
            quiet = now - s["changed"]
            if gone or newer:
                out.append(self.take(s, len(s["text"])))
            elif quiet >= self.stable and (re.search(r"[.?!…。？！]\s*$", s["text"]) or quiet >= 2 * self.stable):
                # A caption that ends without punctuation may be a slow speaker mid-word: give it
                # twice as long before taking it.
                out.append(self.take(s, len(s["text"])))
            elif len(pending) >= self.long:
                cut = max(s["text"].rfind(p, s["done"]) for p in (". ", "? ", "! "))
                if cut > s["done"]:
                    out.append(self.take(s, cut + 1))
        # forget blocks that left the page and are fully emitted
        for bid in [b for b in self.order if b not in ids and self.blocks[b]["done"] >= len(self.blocks[b]["text"])]:
            self.order.remove(bid)
            del self.blocks[bid]
        return [o for o in out if o]

    def flush(self):
        """Emit everything still pending (before switching meetings or stopping)."""
        out = [self.take(s, len(s["text"])) for s in self.blocks.values() if s["text"][s["done"]:].strip()]
        return [o for o in out if o]

    def take(self, s, end):
        text = s["text"][s["done"]:end].strip()
        s["done"] = end
        stamp = time.strftime("%H:%M:%S", time.localtime(s["first"]))
        s["first"] = self.clock()
        key = (s["speaker"], fold(text))
        if not key[1] or UI_NOISE.match(text) or key in self.recent:
            return None
        self.recent = (self.recent + [key])[-30:]
        return stamp, s["speaker"], text


def meeting_tabs(browser, platform="auto"):
    """All open tabs that look like a meeting: [(platform, tab)]."""
    custom = os.environ.get("WINGMAN_CAPTION_URL")    # regex for another meeting site, or for tests
    out = []
    for p in browser.pages():
        url = p.get("url", "")
        if custom and re.search(custom, url):
            out.append((platform if platform != "auto" else "meet", p))
            continue
        for name, rx in PLATFORMS.items():
            if platform in ("auto", name) and rx.match(url):
                out.append((name, p))
    return out


def find_tab(browser, platform, meeting=""):
    """Pick the meeting tab: the one matching `meeting` (title or URL), else the one showing captions."""
    tabs = meeting_tabs(browser, platform)
    if meeting:
        m = meeting.casefold()
        tabs = [t for t in tabs if m in t[1].get("title", "").casefold() or m in t[1].get("url", "").casefold()]
    if len(tabs) <= 1:
        return tabs[0] if tabs else (None, None)
    for name, tab in tabs:          # several: prefer the one that already shows captions
        try:
            s = browser.attach(tab["targetId"])
            r = browser.evaluate(s, EXTRACT % {"platform": json.dumps(name), "custom": json.dumps({})}) or {}
            if r.get("found"):
                return name, tab
        except (RuntimeError, ConnectionError):
            pass
    return tabs[0]


def attach(browser, tab):
    """Attach to the tab and ask Chrome not to throttle it while it is in the background
    (screen sharing, another window in front): otherwise captions arrive minutes late."""
    session = browser.attach(tab["targetId"])
    for method, params in (("Emulation.setFocusEmulationEnabled", {"enabled": True}),
                           ("Page.setWebLifecycleState", {"state": "active"})):
        try:
            browser.call(method, params, session)
        except (RuntimeError, ConnectionError):
            pass
    return session


def write_lines(path, lines, translate):
    if not lines:
        return
    with open(path, "a", encoding="utf-8") as f:
        for stamp, speaker, text in lines:
            f.write(f"[{stamp}] {speaker + ': ' if speaker else ''}{text}\n")
            if translate:
                try:
                    t = translate(text, os.environ.get("WINGMAN_LANG") or "en")
                    if t:
                        f.write(f"[{stamp}] ↳ {translate.target}: {t}\n")
                except Exception as e:
                    print(f"translation failed: {e}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Read live captions from a Meet, Teams or Zoom tab.")
    ap.add_argument("out")
    ap.add_argument("--cdp", default=os.environ.get("WINGMAN_CDP", "main"))
    ap.add_argument("--platform", default="auto", choices=["auto", *PLATFORMS])
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--translate", default=os.environ.get("WINGMAN_TRANSLATE", ""))
    ap.add_argument("--meeting", default="", help="pick the tab whose title or URL contains this text")
    ap.add_argument("--list", action="store_true", help="list the open meeting tabs and exit")
    a = ap.parse_args()

    print(f"connecting to the browser ({a.cdp}); approve 'Allow remote debugging' if the browser asks", flush=True)
    browser = cdp.connect(a.cdp)
    if a.list:
        tabs = meeting_tabs(browser, a.platform)
        if not tabs:
            print("no Meet, Teams or Zoom tab is open in this browser")
        for name, t in tabs:
            print(f"{name:6} {t.get('title', '')[:60]:60} {t.get('url', '')[:70]}")
        return
    translate = None
    if a.translate:
        from translate import Translator
        translate = Translator(a.translate)

    platform, tab, said = None, None, set()
    while tab is None:
        platform, tab = find_tab(browser, a.platform, a.meeting)
        if tab is None:
            if "wait" not in said:
                what = f'a meeting tab matching "{a.meeting}"' if a.meeting else "a Google Meet, Microsoft Teams or Zoom tab (web client)"
                print(f"waiting for {what} to open", flush=True)
                said.add("wait")
            time.sleep(3)
    others = [t for _, t in meeting_tabs(browser, a.platform) if t["targetId"] != tab["targetId"]]
    if others:
        print("other meeting tabs (not read): " + "; ".join(t.get("title", "")[:40] for t in others), flush=True)
    session = attach(browser, tab)
    custom = {"block": os.environ.get("WINGMAN_CAPTION_BLOCK", ""),
              "speaker": os.environ.get("WINGMAN_CAPTION_SPEAKER", ""),
              "text": os.environ.get("WINGMAN_CAPTION_TEXT", "")}
    expr = EXTRACT % {"platform": json.dumps(platform), "custom": json.dumps(custom)}
    print(f"captions ready ({platform}: {tab.get('title', '')[:60]}"
          + (f", translate to {translate.target} on {translate.device}" if translate else "") + ")", flush=True)

    tracker, found_before = Tracker(), None
    control = os.environ.get("WINGMAN_CONTROL", "")
    while True:
        # `wingman switch`: save this meeting's transcript and follow another tab, on the same
        # browser connection (no new "Allow remote debugging?" prompt).
        if control and os.path.exists(control):
            try:
                req = json.load(open(control))
            except ValueError:
                req = {}
            os.remove(control)
            write_lines(a.out, tracker.flush(), translate)
            if req.get("rotate"):
                os.replace(a.out, req["rotate"])
                open(a.out, "w").close()
                print(f"saved transcript to {req['rotate']}", flush=True)
            a.meeting = req.get("meeting", a.meeting)
            name, t = find_tab(browser, a.platform, a.meeting)
            if t:
                platform, tab, session = name, t, attach(browser, t)
                expr = EXTRACT % {"platform": json.dumps(platform), "custom": json.dumps(custom)}
                tracker = Tracker()
                print(f"switched to {platform}: {tab.get('title', '')[:60]}", flush=True)
            else:
                print(f'switch: no meeting tab matching "{a.meeting}"; still reading the old one', flush=True)
        try:
            r = browser.evaluate(session, expr) or {"found": False, "blocks": []}
        except (RuntimeError, ConnectionError) as e:
            print(f"lost the tab ({e}); waiting for it again", flush=True)
            time.sleep(3)
            platform, tab = find_tab(browser, a.platform, a.meeting)
            if tab:
                session = attach(browser, tab)
            continue
        if r["found"] != found_before:
            print("captions visible" if r["found"] else
                  "no captions on the page: turn on captions (CC) in the meeting", flush=True)
            found_before = r["found"]
        write_lines(a.out, tracker.update(r["blocks"]), translate)
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
