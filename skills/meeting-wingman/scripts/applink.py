#!/usr/bin/env python3
"""meeting-wingman applink: record one application's audio (and the microphone) on PipeWire.

`wingman` starts a recorder node that connects to nothing by itself. This helper links the output
ports of the chosen application's streams, and the microphone's capture ports, to that recorder,
and keeps doing so every two seconds, so a stream the app opens later (a new call, a new browser
tab playing audio) is picked up too. The app keeps playing to the speakers as before; nothing in
the user's audio routing is changed.

    applink.py list                                  # applications playing audio right now
    applink.py link --app zoom --rec wingman-rec [--mic alsa_input.usb-...]

Needs PipeWire (pw-dump, pw-link). Standard library only.
"""
import argparse
import json
import re
import subprocess
import sys
import time


def dump():
    try:
        return json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=10).stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []


def props(o):
    return (o.get("info") or {}).get("props") or {}


def streams(objs):
    """Playback streams: (node id, label used for matching, display name)."""
    out = []
    for o in objs:
        p = props(o)
        if o.get("type", "").endswith("Node") and p.get("media.class") == "Stream/Output/Audio":
            names = [p.get(k) or "" for k in ("application.name", "application.process.binary", "node.name", "media.name")]
            label = " ".join(n for n in names if n)
            out.append((o["id"], label, f"{names[0] or names[2]} ({names[1] or '?'}): {names[3]}"))
    return out


def node_ids(objs, name):
    return [o["id"] for o in objs if o.get("type", "").endswith("Node") and props(o).get("node.name") == name]


def ports(objs, node, direction):
    return [o["id"] for o in objs if o.get("type", "").endswith("Port")
            and props(o).get("node.id") == node and props(o).get("port.direction") == direction
            and not props(o).get("port.monitor")]


def links(objs):
    out = set()
    for o in objs:
        if o.get("type", "").endswith("Link"):
            i = o.get("info") or {}
            out.add((i.get("output-port-id"), i.get("input-port-id")))
    return out


def link_once(app_rx, rec_name, mic_name):
    objs = dump()
    rec = node_ids(objs, rec_name)
    if not rec:
        return 0
    rec_in = ports(objs, rec[0], "in")
    if not rec_in:
        return 0
    have = links(objs)
    sources = [nid for nid, label, _ in streams(objs) if app_rx.search(label)]
    if mic_name:
        sources += node_ids(objs, mic_name)
    made = 0
    for src in sources:
        for op in ports(objs, src, "out"):
            for ip in rec_in:   # mono recorder: every output channel goes to its one input (summed)
                if (op, ip) not in have:
                    if subprocess.run(["pw-link", str(op), str(ip)], capture_output=True).returncode == 0:
                        made += 1
    return made


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    lk = sub.add_parser("link")
    lk.add_argument("--app", required=True, help="regex matched against the app name, binary and stream name")
    lk.add_argument("--rec", required=True, help="node.name of the recorder")
    lk.add_argument("--mic", default="", help="node.name of the microphone to mix in")
    lk.add_argument("--once", action="store_true")
    a = ap.parse_args()
    if a.cmd == "list":
        found = streams(dump())
        if not found:
            print("no application is playing audio right now (or this is not PipeWire)")
        for nid, _, disp in found:
            print(f"{nid:>5}  {disp}")
        return
    rx = re.compile(a.app, re.I)
    warned = False
    while True:
        made = link_once(rx, a.rec, a.mic)
        if made:
            print(f"linked {made} port(s) matching /{a.app}/", flush=True)
            warned = False
        elif not warned and not any(rx.search(l) for _, l, _ in streams(dump())):
            print(f"no audio stream matches /{a.app}/ yet; waiting for the app to play sound", flush=True)
            warned = True
        if a.once:
            return
        time.sleep(2)


if __name__ == "__main__":
    sys.exit(main())
