# Contributing

Thanks for helping. Everyone taking part follows the [Code of Conduct](CODE_OF_CONDUCT.md);
security problems go through [SECURITY.md](SECURITY.md), not public issues.

The most useful contributions right now:

- **macOS testing.** Capture through BlackHole is written but has not been tested much.
- **Windows capture** (WASAPI loopback through ffmpeg `dshow`, or another approach).
- **Caption readers for Teams and Zoom**: if `--captions` misses lines or names in a real meeting,
  open an issue with the page's caption DOM (Elements panel, the caption area only, with names
  removed) or a PR against `EXTRACT` in `captions.py`.
- **Trigger patterns** for more languages in `gate.py`, with a test in `tests/test_gate.py`.
- **Hallucination filters** for more languages: the phrases Whisper invents during silence in your
  language, added to `HALLUCINATIONS` in `transcribe_server.py`.
- **Coaching rules** in `SKILL.md` that you have seen work in real meetings.

## Layout

| Path | |
|---|---|
| `skills/meeting-wingman/SKILL.md` | What Claude does before, during and after the meeting |
| `skills/meeting-wingman/scripts/wingman` | Start, watch, stop the pipeline (bash) |
| `skills/meeting-wingman/scripts/transcribe_server.py` | The faster-whisper transcriber |
| `skills/meeting-wingman/scripts/segmenter.py` | Cuts audio at pauses (standard library only) |
| `skills/meeting-wingman/scripts/gate.py` | Decides which lines wake Claude (standard library only) |
| `skills/meeting-wingman/scripts/applink.py` | Links one app's audio to the recorder on PipeWire (`--app`) |
| `skills/meeting-wingman/scripts/captions.py`, `cdp.py` | Reads Meet/Teams/Zoom captions from the browser |
| `tests/` | Unit tests and a mock Meet page |
| `skills/meeting-wingman/templates/prep-notes.md` | Prep document template |
| `.claude-plugin/` | Plugin and marketplace manifests |

## Before you open a PR

```bash
shellcheck skills/meeting-wingman/scripts/wingman
python3 -m py_compile skills/meeting-wingman/scripts/*.py
python3 -m unittest discover -s tests -v      # the browser test needs Chrome or Chromium
claude plugin validate .
```

Then do a real run: `wingman start --local -l en`, play some speech, `wingman stop /tmp/t.txt`,
and check that no `transcribe_server` or `ffmpeg` process is left behind.

If you change behaviour, bump `version` in `.claude-plugin/plugin.json` and add a
`CHANGELOG.md` entry; CI checks that the two match.

Never commit real transcripts, recordings or prep notes from real meetings, not even in tests.
