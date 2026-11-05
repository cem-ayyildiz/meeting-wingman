# meeting-wingman

**A live wingman for your Meet, Teams and Zoom calls, inside Claude Code. It tells you what to say when the hard question comes, and turns what your team agrees on into tasks while the meeting is still running.**

[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e?style=flat-square)](LICENSE)
[![Claude Code plugin](https://img.shields.io/badge/Claude_Code-plugin-d97757?style=flat-square)](#install)
[![Works with](https://img.shields.io/badge/works_with-Meet_%7C_Teams_%7C_Zoom-7c3aed?style=flat-square)](#works-with-meet-teams-and-zoom)
[![Platform](https://img.shields.io/badge/platform-Linux_%7C_macOS_(beta)-0891b2?style=flat-square)](#requirements)
[![CI](https://img.shields.io/github/actions/workflow/status/cem-ayyildiz/meeting-wingman/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/cem-ayyildiz/meeting-wingman/actions/workflows/ci.yml)
[![Stars](https://img.shields.io/github/stars/cem-ayyildiz/meeting-wingman?style=flat-square)](https://github.com/cem-ayyildiz/meeting-wingman/stargazers)

<p align="center">
  <img src="docs/assets/hero.svg" width="900" alt="On the left, the live transcript of a call. On the right, Claude's suggested answer to the question just asked, with a one-line warning of what not to say.">
</p>

**Coach mode.** You are on a client call. Someone asks the question you were hoping to avoid.
meeting-wingman has been transcribing the call since it started. About 20 seconds later, a card
with three bullets appears: what to say, with your own numbers from your prep notes, and one thing
**not** to say.

**Team mode.** In your weekly sync, Maria says she will fix the CSV export by Thursday. A task
appears in ClickUp (or Linear, Jira, GitHub, Asana) with her as owner. Someone mentions the SSO
login is still blocked, and that becomes a comment on the existing task instead of a duplicate.
You confirm each one with a word, or let it write on its own.

No bot joins the call. It hears what your computer's speakers play, transcribes it on a GPU when
one is free and on the CPU otherwise, and can translate every line into your language as it goes.

```
/plugin marketplace add cem-ayyildiz/meeting-wingman
/plugin install meeting-wingman@meeting-wingman
```

Then tell Claude: *"I'm joining a client call in ten minutes. Listen and help me with the questions."*
or *"Listen to our standup and put the action items into ClickUp."*

---

## Coach mode

For meetings where you have to answer: clients, interviews, reviews, investors. Every new line of
the transcript reaches Claude. It answers in one of four ways and keeps each reply short, because
you are reading while you talk.

| When | Claude writes |
|---|---|
| Small talk, presentation, no question | `No question.` |
| Someone asks you something | **❓ The question in a few words**, then 2–3 bullets you can say as they are, with numbers. If there is a trap, one `Don't say:` line |
| Someone on your side says a wrong number, a wrong date or an overclaim | One line with the correct version |
| The meeting reaches a part you present | A 2–3 bullet reminder |

Before the meeting it helps you prepare: a term list so names and acronyms come out right, and,
if you want one, a prep document with likely questions and 60-second answers
([template](skills/meeting-wingman/templates/prep-notes.md)). Afterwards it saves the transcript,
summarises which answers were weak, and lists what you promised to send.

## Team mode

<p align="center">
  <img src="docs/assets/team.svg" width="900" alt="On the left, the live transcript of a team sync. On the right, a new task created for Maria with a Thursday due date, and a comment proposed on the existing SSO task.">
</p>

For internal meetings: standups, planning, project syncs. Before the meeting Claude loads the
list or project from your tracker, its members and its open tasks. During the meeting:

| Heard | Claude does |
|---|---|
| "Maria, can you get the CSV fix out before Thursday?" | **New task**, owner Maria, due Thursday |
| "SSO is still blocked, we're waiting on their IT" | **Comment** on the open SSO task, not a duplicate |
| "OK, we go with option B" | **Comment** with the decision on the related task |
| A problem nobody picks up | **New task**, unassigned, flagged |

You choose how much it writes on its own: `confirm` (default, you answer "ok"), `auto` (writes
at once and shows the link) or `end` (collects everything and writes after you review the list).
It assigns only people who are in the workspace, follows the workspace's language and
conventions, and never pastes the transcript into a task.

Any tracker Claude Code can reach works: an MCP server (ClickUp, Linear, Jira, Asana, Notion) or a
CLI (`gh` for GitHub Issues). Without one, the items go to a file.

## Works with Meet, Teams and Zoom

meeting-wingman listens to the computer's audio output, so it does not care which app plays it:
Google Meet, Microsoft Teams and Zoom, in the browser or as desktop apps, and anything else that
makes sound (Webex, Slack huddles, Discord, a phone call through the computer). Nothing is
installed in the meeting and no bot joins it.

## Translation

Add `-x <language>` and every line gets a translation underneath, from a local
[NLLB-200](https://huggingface.co/facebook/nllb-200-distilled-600M) model through CTranslate2
(the same engine faster-whisper uses, so nothing new to install):

```
[13:05:51] Pilot sahada üç ay sorunsuz çalıştı, şimdi ikinci aşamayı planlıyoruz.
[13:05:51] ↳ en: The pilot's been in the field for three months, and we're planning a second phase.
```

The meeting can be in any of Whisper's ~100 languages and the translation in any of NLLB's 200.
A sentence takes about 0.3–0.4 s on a laptop CPU. The model is downloaded on first use: 0.6 GB
(600M, CPU) or 1.4 GB (1.3B, GPU). NLLB-200 is licensed **CC-BY-NC-4.0** (non-commercial); set
`WINGMAN_TRANSLATE_MODEL` to another CTranslate2 NLLB-compatible model if that does not fit.

## How it works

<p align="center">
  <img src="docs/assets/how-it-works.svg" width="900" alt="Meeting app, then system audio captured by ffmpeg in 20-second chunks, then faster-whisper on your CPU, GPU or an SSH host, then Claude Code with its Monitor tool and your prep notes, then you.">
</p>

1. `ffmpeg` records the system audio monitor in 20-second chunks: whatever the meeting app plays,
   including your own voice coming back from the call.
2. [faster-whisper](https://github.com/SYSTRAN/faster-whisper) turns each chunk into a
   timestamped line, optionally with a translation: `large-v3` on a GPU, `small` on a CPU, locally
   or on another machine over SSH. If the GPU is missing, busy or out of memory, it falls back to
   the CPU by itself.
3. Claude Code follows the transcript with its Monitor tool and replies to every new line: answer
   suggestions in coach mode, tasks and comments in team mode.

**Recommended setup:** speak from your phone, and join the same meeting from your computer with
mic and camera off. Your voice comes back through the meeting app, so nothing else needs to be
captured, and you can mute the computer's speakers. On Linux, capture taps the audio before the
volume control, so there is no echo.

## Install

**Claude Code (recommended):**

```
/plugin marketplace add cem-ayyildiz/meeting-wingman
/plugin install meeting-wingman@meeting-wingman
```

<details>
<summary><strong>From the terminal, or without the plugin system</strong></summary>

```bash
claude plugin marketplace add cem-ayyildiz/meeting-wingman
claude plugin install meeting-wingman@meeting-wingman
```

Or copy the skill by hand:

```bash
git clone https://github.com/cem-ayyildiz/meeting-wingman
cp -r meeting-wingman/skills/meeting-wingman ~/.claude/skills/
```

</details>

**Updates:** Claude Code does not update third-party plugins automatically by default. Run
`/plugin`, open **Marketplaces**, select **meeting-wingman** and turn on auto-update, or run
`/plugin marketplace update meeting-wingman`.

Other agents: the skill depends on Claude Code's Monitor tool to receive transcript lines while
you talk, so for now it works in Claude Code only.

## Requirements

| | Linux | macOS (beta) |
|---|---|---|
| Audio capture | PulseAudio or PipeWire (`pipewire-pulse`), works out of the box | A loopback device such as [BlackHole](https://github.com/ExistentialAudio/BlackHole) plus a Multi-Output Device (speakers + BlackHole) |
| Tools | `ffmpeg`, `bash`, Python 3.9+ | `ffmpeg`, `bash`, Python 3.9+ |
| Transcription | `pip install faster-whisper` | `pip install faster-whisper` |

Windows is not supported yet.

A CPU is enough: the `small` model keeps up in real time with lower accuracy. With an NVIDIA GPU
you get `large-v3` (about 4 GB of GPU memory), which handles names and mixed languages much
better. When the GPU cannot be used at start-up, both transcription and translation load on the
CPU instead and `wingman start` tells you so. If the GPU is on another machine, see [Remote GPU](#remote-gpu).

## Configuration

Nothing is required. To change the defaults, put `KEY=value` lines in
`~/.config/meeting-wingman/config`.

<details>
<summary><strong>All settings</strong></summary>

| Variable | Default | |
|---|---|---|
| `WINGMAN_REMOTE_HOST` | (none) | SSH host that runs the transcription |
| `WINGMAN_REMOTE_PYTHON` | `python3` | Python with faster-whisper on that host |
| `WINGMAN_REMOTE_DIR` | `.meeting-wingman` | Working directory on that host, relative to home |
| `WINGMAN_PYTHON` | `python3` | Local Python with faster-whisper |
| `WINGMAN_MODEL` | `large-v3` on GPU, `small` on CPU | Any faster-whisper model, e.g. `large-v3-turbo`, `medium`. With a remote host it applies to the host; the local fallback picks by device |
| `WINGMAN_DEVICE` | `auto` | `cuda` or `cpu`. `auto` tries the GPU and falls back to the CPU |
| `WINGMAN_TRANSLATE_MODEL` | 1.3B on GPU, 600M on CPU | CTranslate2 NLLB model for `-x` (Hugging Face repo or local path) |
| `WINGMAN_TRANSLATE_DEVICE` | `auto` | Same as `WINGMAN_DEVICE`, for the translator |
| `WINGMAN_CHUNK` | `20` | Seconds per chunk. Shorter = lower latency, worse accuracy |
| `WINGMAN_AUDIO_SOURCE` | Linux `@DEFAULT_MONITOR@`, macOS `BlackHole 2ch` | What to capture |
| `WINGMAN_MIC` | (none) | A second source mixed in, e.g. your microphone |

</details>

### Remote GPU

```
WINGMAN_REMOTE_HOST=gpu-box
WINGMAN_REMOTE_PYTHON=~/venvs/whisper/bin/python
```

The host needs Python with faster-whisper. This machine needs `rsync` and an SSH key that works
without a prompt. If SSH fails or the model does not load on the host (for example, the GPU is out
of memory), `wingman start` says so and falls back to local transcription within seconds, so the
meeting is never left without a transcript.

## The `wingman` command

Claude runs it for you. You can also run it yourself
([`skills/meeting-wingman/scripts/wingman`](skills/meeting-wingman/scripts/wingman)):

```bash
wingman start -l en -t "Acme, Project Falcon, SOC 2"   # language + recognition hints
wingman start -l ja -x en                              # Japanese call, English under each line
wingman watch                                          # follow the transcript
wingman level                                          # is any audio being captured?
wingman stop notes/client-call-transcript.txt          # stop and save
wingman status
```

State lives in `~/.local/state/meeting-wingman/`.

## Limits

- **About 20–25 seconds behind.** Fine for questions, which take time to finish anyway. Too slow
  for word-by-word prompting.
- **No speaker labels.** Claude infers who is talking from the content.
- **Names and acronyms come out garbled** without a term list, and sometimes with one. Claude reads for meaning.
- **Translation is literal**, sentence by sentence, and weaker on the CPU model. Claude reads the
  original for meaning and numbers.
- **It only hears the computer.** If you are in the room with the other person, this is the wrong tool.

## Consent and privacy

This tool transcribes other people. In many places you must tell the other participants, or get
their consent, before you do that, and company policies may forbid it. The skill reminds you at the
start; using it lawfully is your responsibility.

Audio and transcripts stay on your machine or your own SSH host. Transcript lines are read by
Claude Code, so they go to the model provider like everything else in your session.

## Troubleshooting

<details>
<summary><strong>No line ever arrives</strong></summary>

Run `wingman level`. Around −60 dB or lower means nothing is playing: the computer is not in the
meeting, the app or tab is muted, or the default output device is wrong (Linux: `wpctl status`).
</details>

<details>
<summary><strong>The transcript contains sentences nobody said</strong></summary>

Whisper invents text during silence ("Thank you for watching", subtitle credits, or the hint list
read back). The common ones are filtered. Add the ones in your language to `HALLUCINATIONS` in
[`transcribe_server.py`](skills/meeting-wingman/scripts/transcribe_server.py), and please send a PR.
</details>

<details>
<summary><strong>Lines stop arriving in remote mode</strong></summary>

`ssh <host> 'ls .meeting-wingman/in; tail .meeting-wingman/server.log'`. If chunks pile up, the
server has died: `wingman stop`, then `wingman start` again.
</details>

## Contributing

Issues and PRs are welcome, especially macOS testing, Windows capture, and hallucination filters
for more languages. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
