# Contributing

Thanks for helping. The most useful contributions right now:

- **macOS testing.** Capture through BlackHole is written but has not been tested much.
- **Windows capture** (WASAPI loopback through ffmpeg `dshow`, or another approach).
- **Hallucination filters** for more languages: the phrases Whisper invents during silence in your
  language, added to `HALLUCINATIONS` in `transcribe_server.py`.
- **Coaching rules** in `SKILL.md` that you have seen work in real meetings.

## Layout

| Path | |
|---|---|
| `skills/meeting-wingman/SKILL.md` | What Claude does before, during and after the meeting |
| `skills/meeting-wingman/scripts/wingman` | Start, watch, stop the pipeline (bash) |
| `skills/meeting-wingman/scripts/transcribe_server.py` | The faster-whisper transcriber |
| `skills/meeting-wingman/templates/prep-notes.md` | Prep document template |
| `.claude-plugin/` | Plugin and marketplace manifests |

## Before you open a PR

```bash
shellcheck skills/meeting-wingman/scripts/wingman
python3 -m py_compile skills/meeting-wingman/scripts/transcribe_server.py
claude plugin validate .
```

Then do a real run: `wingman start --local -l en`, play some speech, `wingman stop /tmp/t.txt`,
and check that no `transcribe_server` or `ffmpeg` process is left behind.

If you change behaviour, bump `version` in `.claude-plugin/plugin.json` and add a
`CHANGELOG.md` entry; CI checks that the two match.

Never commit real transcripts, recordings or prep notes from real meetings, not even in tests.
