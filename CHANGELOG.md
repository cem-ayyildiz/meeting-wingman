# Changelog

## [0.1.1] - 2026-11-05

- README rewritten: demo image, pipeline diagram, limits, troubleshooting.
- CI (shellcheck, Python syntax, manifest and version checks), contributing guide, issue template.

## [0.1.0] - 2026-11-05

First public release, generalised from a private tool used in real review meetings.

- `wingman` command: `start`, `watch`, `stop`, `level`, `status`.
- Local transcription by default (`large-v3` on GPU, `small` on CPU); optional remote GPU over SSH.
- Falls back to local transcription when SSH fails or the remote model does not load.
- Linux capture through PulseAudio/PipeWire; macOS through a loopback device (beta).

Lessons from those meetings that are built in:

- Whisper invents sentences during silence ("Thank you for watching", subtitle credits, the hint
  list read back). The server filters them; Turkish `İ`/`ı` are normalised before matching.
- `condition_on_previous_text` made the model repeat the previous sentence for minutes on muffled
  audio. It is off.
- Chunks are ordered by name, not modification time, and leftovers are cleared on start;
  otherwise half-written chunks were shipped.
- `pkill -f` over SSH killed its own remote shell. PID files are used instead.
- Long jobs started from an agent's background shell can be killed at a time limit. Everything
  runs under `setsid`.
