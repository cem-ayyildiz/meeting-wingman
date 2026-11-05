# meeting-wingman

A live meeting coach for [Claude Code](https://claude.com/claude-code).

While you are in an online meeting, meeting-wingman transcribes whatever your computer plays
(Zoom, Meet, Teams, anything) with [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
and streams the lines into your Claude Code session. When someone asks a question, Claude
suggests a short answer you can say, and warns you in one line when there is a trap.
Afterwards it saves the transcript and lists what you promised.

```
**❓ Why not use the off-the-shelf alternative?**
- It covers the 80% case; our customers are in the other 20%: offline sites, 3 s latency budget.
- We benchmarked it in March: 2.4× the cost per device at our volume.
- We can still integrate with it; the two are not exclusive.
**Don't say:** "nobody else can do this."
```

It works best with a prep document (`templates/prep-notes.md`): likely questions, 60-second
answers, and the sentences that went badly last time.

## How it works

    meeting app ─► system audio monitor ─► ffmpeg, 20 s WAV chunks
                                              │ (local dir, or rsync to a GPU host)
                                              ▼
                              transcribe_server.py (faster-whisper)
                                              │ "[HH:MM:SS] text" lines
                                              ▼
                              transcript.txt ─► wingman watch ─► Claude Code Monitor tool

Each line arrives about 20–25 seconds after it was spoken. There is no speaker separation.

The recommended setup: speak from your phone, and join the same meeting from the computer with
mic and camera off. Your own voice comes back through the meeting app, so only the computer's
output needs to be captured, and you can mute the computer's speakers (on Linux, capture taps the
audio before the volume control).

## Requirements

- Claude Code (uses the Monitor tool)
- `ffmpeg`, `bash`, Python 3.9+ with `pip install faster-whisper`
- **Linux** with PulseAudio or PipeWire (`pipewire-pulse`): works out of the box.
- **macOS** (experimental): install a loopback device such as
  [BlackHole](https://github.com/ExistentialAudio/BlackHole), create a Multi-Output Device
  (speakers + BlackHole) and make it the output. Set `WINGMAN_AUDIO_SOURCE` if your device name
  differs from `BlackHole 2ch`. `setsid` is not available on macOS, so the pipeline runs under `nohup` only.
- Windows: not supported yet.

Speed: on a CPU the default model is `small` (fast, lower accuracy). With an NVIDIA GPU it is
`large-v3` (about 4 GB of GPU memory). You can also run the transcription on another machine with
a GPU over SSH (see Configuration); then that machine needs Python + faster-whisper, and this one
needs `rsync` and an SSH key that works without a prompt.

## Install

As a Claude Code plugin:

```
/plugin marketplace add cem-ayyildiz/meeting-wingman
/plugin install meeting-wingman@meeting-wingman
```

Or copy the skill by hand:

```
git clone https://github.com/cem-ayyildiz/meeting-wingman
cp -r meeting-wingman/skills/meeting-wingman ~/.claude/skills/
```

Then, in Claude Code: *"I'm joining a client call in 10 minutes, listen and help me with questions."*

## Configuration

Optional. Put `KEY=value` lines in `~/.config/meeting-wingman/config`:

| Variable | Default | |
|---|---|---|
| `WINGMAN_REMOTE_HOST` | (none) | SSH host that runs the transcription (e.g. a GPU box) |
| `WINGMAN_REMOTE_PYTHON` | `python3` | Python with faster-whisper on that host, e.g. `~/venvs/whisper/bin/python` |
| `WINGMAN_REMOTE_DIR` | `.meeting-wingman` | Working directory on that host, relative to home |
| `WINGMAN_PYTHON` | `python3` | Local Python with faster-whisper |
| `WINGMAN_MODEL` | `large-v3` on GPU, `small` on CPU | Any faster-whisper model, e.g. `large-v3-turbo`, `medium`. With a remote host it applies to the host; the local fallback picks by device |
| `WINGMAN_DEVICE` | `auto` | `cuda` or `cpu` |
| `WINGMAN_CHUNK` | `20` | Seconds per chunk. Shorter = lower latency, worse accuracy |
| `WINGMAN_AUDIO_SOURCE` | Linux `@DEFAULT_MONITOR@`, macOS `BlackHole 2ch` | What to capture |
| `WINGMAN_MIC` | (none) | A second source mixed in, e.g. your microphone |

Example for a GPU server:

```
WINGMAN_REMOTE_HOST=gpu-box
WINGMAN_REMOTE_PYTHON=~/venvs/whisper/bin/python
```

If the SSH key is not loaded, `wingman start` warns and falls back to local transcription.

## The `wingman` command

Claude runs it for you, but it works on its own too
(`skills/meeting-wingman/scripts/wingman`):

```
wingman start -l en -t "Acme, Project Falcon, SOC 2"   # language + recognition hints
wingman watch                                          # follow the transcript
wingman level                                          # is any audio being captured?
wingman stop notes/client-call-transcript.txt          # stop and save
```

State lives in `~/.local/state/meeting-wingman/`.

## Consent and privacy

This tool records and transcribes other people. In many places you must tell the other
participants, or get their consent, before doing that; company policies may also forbid it. You
are responsible for using it lawfully.

Audio and transcripts stay on your machine (or your own SSH host). The transcript lines are read by
Claude Code, so they are sent to the model provider like anything else in your session.

## Lessons built in

- Whisper invents sentences during silence ("Thank you for watching", subtitle credits, or the
  hint list read back). The server filters the common ones; add your language's to
  `HALLUCINATIONS` in `transcribe_server.py`.
- `condition_on_previous_text` made the model repeat the previous sentence for minutes on muffled
  audio. It is off.
- Chunks are ordered by name, not modification time, and leftovers are cleared on start; otherwise
  half-written chunks get shipped.
- Never `pkill -f` the server over SSH: the remote shell's own command line matches and it kills
  itself. PID files are used instead.
- Everything runs detached, because an agent's background jobs can be killed at a time limit.

## License

MIT
