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
meeting-wingman has been following the call since it started. Two seconds after they stop talking, a card
with three bullets appears: what to say, with your own numbers from your prep notes, and one thing
**not** to say.

**Team mode.** In your weekly sync, Maria says she will fix the CSV export by Thursday. A task
appears in ClickUp (or Linear, Jira, GitHub, Asana) with her as owner. Someone mentions the SSO
login is still blocked, and that becomes a comment on the existing task instead of a duplicate.
You confirm each one with a word, or let it write on its own.

We use it every day as a helper in our own internal meetings at FreshSens: standups, firmware and
software syncs, sales updates.

No bot joins the call. It either reads the meeting's own captions in your browser (with speaker
names) or listens to your computer's audio and transcribes it, on a GPU when one is free and on
the CPU otherwise. It can translate every line into your language as it goes, and it only wakes
Claude for what matters: questions, your name, commitments, decisions, numbers.

```
/plugin marketplace add cem-ayyildiz/meeting-wingman
/plugin install meeting-wingman@meeting-wingman
```

Then tell Claude: *"I'm joining a client call in ten minutes. Listen and help me with the questions."*
or *"Listen to our standup and put the action items into ClickUp."*

---

## Examples

Say it in your own words; these are the kinds of requests the skill is built for.

1. *"I have an investor call on Zoom in 15 minutes. Read `notes/q3-numbers.md`, then listen and
   help me answer their questions."* Claude reads the notes, starts the transcription, and from
   then on answers every question with a short card.
2. *"Listen to our weekly sync on Teams and put the action items into the Sprint 42 list in
   ClickUp. Ask me before you create anything."* Claude loads the list, its members and open
   tasks, and proposes each task or comment for a one-word "ok".
3. *"This Meet call is in Japanese. Transcribe it and give me an English translation of every
   line."* Claude starts with `-l ja -x en` and the English line appears under each Japanese one.
4. *"The meeting is over. Save the transcript to `meetings/` and list what we promised to send."*

## Use cases

Tell Claude which meeting and what you need; it picks the source, the mode and the target, and
starts in a few seconds, also when the meeting is already running.

| Situation | Say to Claude | What it runs |
|---|---|---|
| Investor or client call in the **Zoom desktop app** | *"Help me answer questions in this Zoom call; my numbers are in `notes/q3.md`."* | `wingman start -m coach --app zoom -n Ana` |
| **Daily standup in Google Meet** (browser), tasks in ClickUp | *"Follow the standup in Meet and put action items into Sprint 42. Ask before creating."* | `wingman start -m team --captions -n Ana` |
| **Two meetings open** (one on hold, back-to-back calls) | *"Follow the one called Weekly sync, not the other."* | `wingman meetings`, then `--captions --meeting "Weekly sync"` or `--app teams` |
| **Already in the meeting**, ten minutes late | *"Start now."* | Starts at once; with captions it also picks up what is still on screen |
| **Switch** to the next call | *"Switch to the Teams call."* | `wingman stop` (saves this one), `wingman start --app teams ...` |
| Meeting in a **language you don't speak** | *"This call is in Japanese, translate everything to English."* | `wingman start -l ja -x en` |
| **Job interview** as the candidate | *"Coach me through this interview; here is the job post and my CV."* | Prep notes from both, then `-m coach` |
| **Webinar or all-hands**, listening only | *"Listen and give me the decisions and anything about our team."* | `-m team -n "Ana, Platform team"`, summary at the end |
| You **dial in by phone**, the laptop only listens | *"I'm on the phone, the laptop is just in the call."* | adds `--no-mic` |
| Laptop without a GPU, a **GPU box** at home or work | (configured once) | `WINGMAN_REMOTE_HOST=gpu-box`; falls back to the laptop CPU if the box is busy |
| Something else is playing (music, a video) | *"Only listen to Teams."* | `--app teams` records just that app (PipeWire) |

`wingman meetings` lists what can be followed right now: the apps playing audio and the Meet,
Teams and Zoom tabs open in the browser.

## Coach mode

For meetings where you have to answer: clients, interviews, reviews, investors. A local filter
watches the transcript and wakes Claude only for questions, your name and numbers; the rest
reaches it as a digest every few minutes, so the screen stays quiet until something needs you.
Each reply is short, because you are reading while you talk.

| When | Claude writes |
|---|---|
| Small talk, presentation, no question | Nothing (it arrives later in a digest) |
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

Two sources, pick per meeting:

| | **Captions** (`--captions`) | **Audio** (default) |
|---|---|---|
| Works with | Meet, Teams and Zoom **in the browser** (Chrome, Edge, Chromium), captions turned on | Any app that makes sound: Meet, Teams, Zoom desktop or browser, Webex, Slack huddles, Discord |
| Speaker names | Yes, from the meeting | No |
| Needs | Remote debugging on (`chrome://inspect/#remote-debugging`); the browser asks you to allow it. See [the note below](#what-allow-remote-debugging-grants) | `ffmpeg` and faster-whisper; a GPU helps |
| Latency | About 2 s after a caption settles | 1–3 s after the speaker pauses |
| Languages | Those the platform captions | Whisper's ~100 |

### What "Allow remote debugging" grants

> [!WARNING]
> Captions are optional. If you do not allow remote debugging, use the audio source: it works
> with every meeting app, only without speaker names. If you do allow it, know that the
> permission is not limited to captions. When you click **Allow**, the connection can control
> the **whole browser**: every open tab, the pages you are signed in to and their content.
> meeting-wingman uses it only to list the open tabs (address and title) and to read the caption
> text of the meeting tab, and its code is short enough to check
> ([`captions.py`](skills/meeting-wingman/scripts/captions.py), [`cdp.py`](skills/meeting-wingman/scripts/cdp.py)).
> But the grant itself is wider than that, and while remote debugging is on, any program on your
> computer can ask for the same access (the browser asks you again for each new connection).
>
> - **Turn it off after the meeting:** open `chrome://inspect/#remote-debugging` (or `edge://inspect`)
>   and switch remote debugging off. Turn it on again before the next captions meeting.
> - **Safer: a separate browser.** Start a browser with its own profile,
>   `google-chrome --user-data-dir=$HOME/.config/wingman-chrome --remote-debugging-port=9222`, join
>   the meeting there and use `wingman start --captions --cdp 9222`. The connection then reaches
>   only that profile, not your main browser with its sign-ins.
> - **Or use the audio source**, which does not touch the browser at all.

Captions are best for team meetings, where it matters who said "I'll take it". Audio works
everywhere, including the desktop apps. Nothing is installed in the meeting and no bot joins it.

Tested in real meetings (November 2026): **Meet** and **Teams** web captions work well with speaker
names. **Zoom**'s caption overlay arrives in fragments and without names, so for Zoom use the audio
source (`--app chrome` for the web client, `--app zoom` for the desktop app) or turn on Zoom's full
transcript. Platforms change their pages; please [report](https://github.com/cem-ayyildiz/meeting-wingman/issues) what breaks.
If a platform changes its page, `WINGMAN_CAPTION_BLOCK`, `WINGMAN_CAPTION_SPEAKER` and
`WINGMAN_CAPTION_TEXT` take CSS selectors without waiting for a release.

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
  <img src="docs/assets/how-it-works.svg" width="900" alt="The meeting reaches the transcript either as captions read from the browser or as audio cut at pauses and transcribed by faster-whisper; a local filter passes only the lines that matter to Claude Code, which shows you answers and tasks.">
</p>

1. **Captions source:** a small DevTools client reads the caption blocks of the Meet, Teams or Zoom
   tab once a second and writes each settled caption as `[time] Speaker: text`.
   **Audio source:** `ffmpeg` records the system audio and your microphone; a voice-activity
   segmenter cuts at pauses, so silence is never transcribed;
   [faster-whisper](https://github.com/SYSTRAN/faster-whisper) turns each utterance into a line
   (`large-v3` on a GPU, `small` on a CPU, locally or on another machine over SSH, falling back to
   the CPU when the GPU is missing, busy or out of memory).
2. Optionally a local NLLB model adds a translated line under each line.
3. `wingman watch`, a local filter, sends Claude Code an event only for lines that match the mode
   (questions, your name, numbers in coach mode; commitments, decisions, blockers, dates in team
   mode), with the quiet lines before it as context, and a digest of the rest every few minutes.
4. Claude replies: answer cards in coach mode, tasks and comments in team mode.

### What runs where

<p align="center">
  <img src="docs/assets/architecture.svg" width="900" alt="Architecture. On your computer: captions from the browser tab (optional, needs the browser's permission), or audio (the default) transcribed by faster-whisper, go into one transcript; a filter wakes Claude Code, which shows you answers and tasks. Outside your computer, only if you use them: models from the Hugging Face Hub once, your own SSH GPU host, the model provider through your Claude Code session, and your task tracker after you confirm.">
</p>

| Part | Where it runs | What crosses the network |
|---|---|---|
| Caption reader (`captions.py`, `cdp.py`), **optional** | Your computer, talking to your browser on `127.0.0.1`. Runs only with `--captions` and only after you allow remote debugging in the browser; without that, use the audio source | Nothing |
| Recorder and segmenter (`ffmpeg` or `pw-record`, `segmenter.py`) | Your computer | Nothing |
| Transcriber and translator (`transcribe_server.py`, `translate.py`) | Your computer, or the SSH host you configure | Models from the Hugging Face Hub, once. In remote mode, audio chunks to your host and lines back |
| Filter (`gate.py`, `wingman watch`) | Your computer | Nothing |
| Claude Code | Your computer | The lines the filter passes, like any text in your session |
| Your tracker | Its own service | Tasks and comments in team mode, after you confirm (or with `auto`) |

Everything inside the box is started and stopped by the `wingman` command; there is no daemon,
no service and nothing left running after `wingman stop`.

**Recommended setup:** run Claude Code in **VS Code** (or another editor with the Claude Code
panel) beside the meeting window, so the cards are next to the call. Join from the computer as you
normally do; with the audio source your microphone is recorded too. If you speak from another
device (a phone dialled into the meeting), add `--no-mic`.

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

**Claude Code only.** The plugin records audio and runs local programs, and it needs Claude
Code's Monitor tool to receive transcript lines while you talk, so it does not work in claude.ai
chat or Cowork. Inside Claude Code the plugin also puts a `wingman` command on the PATH.

## Requirements

| | Linux | macOS (beta) |
|---|---|---|
| Audio capture | PulseAudio or PipeWire (`pipewire-pulse`), works out of the box | A loopback device such as [BlackHole](https://github.com/ExistentialAudio/BlackHole) plus a Multi-Output Device (speakers + BlackHole) |
| Tools | `ffmpeg`, `bash`, Python 3.9+ | `ffmpeg`, `bash`, Python 3.9+ |
| Transcription (audio source) | `pip install faster-whisper` | `pip install faster-whisper` |
| Captions source | Chrome, Edge or Chromium; nothing to install | the same |

Windows is not supported yet. Run `wingman doctor` once: it checks each of these and says what is missing.

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
| `WINGMAN_PAUSE` | `0.7` | Pause in seconds that ends an utterance |
| `WINGMAN_MAX_CHUNK` | `15` | Longest utterance before a forced cut |
| `WINGMAN_AUDIO_SOURCE` | Linux `@DEFAULT_MONITOR@`, macOS `BlackHole 2ch` | System audio to capture |
| `WINGMAN_MIC` | `auto` | `auto` (the default microphone), `none`, or a source name. A Bluetooth headset switches to headset mode when its microphone opens; in a call the app already does this |
| `WINGMAN_DIGEST` | `300` | Seconds between digests of lines that woke nobody |
| `WINGMAN_NAMES` | (none) | Your name(s), so "Ana, what do you think?" wakes Claude (same as `-n`) |
| (option) `--app NAME` | everything | Record only one application's audio, matched by name: `zoom`, `teams`, `chrome`, `firefox`. Needs PipeWire; the app keeps playing to your speakers |
| (option) `--meeting TEXT` | the tab showing captions | With `--captions`, the tab whose title or URL contains TEXT |
| `WINGMAN_CDP` | `main` | Browser for `--captions`: `main` (your own, via its DevToolsActivePort) or a debugging port |

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
wingman doctor                                          # check the setup once
wingman meetings                                        # apps playing audio, meeting tabs open
wingman start -m coach --app zoom                       # only the Zoom app's audio
wingman start -m coach -n Ana -l en -t "Acme, SOC 2"   # audio, wake on questions, your name, numbers
wingman start -m team -n Ana --captions                 # captions from the browser tab
wingman start --captions --meeting "Weekly sync"        # that tab, when several are open
wingman start -l ja -x en                               # Japanese call, English under each line
wingman watch                                           # events for Claude (--raw: every line)
wingman show 60                                         # the last 60 lines
wingman level                                           # system audio and microphone levels
wingman switch --meeting "Weekly sync" notes/standup.txt  # captions: save this one, follow another tab
wingman stop notes/client-call-transcript.txt           # stop and save, keep no other copy
wingman status
```

State lives in `~/.local/state/meeting-wingman/`.

## Limits

- **A second or two behind,** plus the time Claude takes to write the card.
- **No speaker labels with the audio source.** Use captions when names matter.
- **The filter is keyword-based.** It catches most questions and commitments in English, Turkish,
  German, French, Spanish, Italian, Dutch and Portuguese; the digest covers what it misses.
- **Names and acronyms come out garbled** without a term list, and sometimes with one. Claude reads for meaning.
- **Translation is literal**, sentence by sentence, and weaker on the CPU model. Claude reads the
  original for meaning and numbers.
- **It only hears the computer.** If you are in the room with the other person, this is the wrong tool.

## What it runs, sends and fetches

Everything the plugin does is in readable bash and Python in
[`skills/meeting-wingman/scripts/`](skills/meeting-wingman/scripts/). The only executable outside
that folder is [`bin/wingman`](bin/wingman), a four-line wrapper that puts `wingman` on the PATH
inside Claude Code and runs `skills/meeting-wingman/scripts/wingman` with the same arguments; it
does nothing else.

| | |
|---|---|
| **Executables shipped** | [`bin/wingman`](bin/wingman) (the wrapper above), [`scripts/wingman`](skills/meeting-wingman/scripts/wingman) (bash, the command itself) and [`scripts/transcribe_server.py`](skills/meeting-wingman/scripts/transcribe_server.py) (Python, the transcriber). The other `.py` files are run with `python3`. Nothing is compiled or installed, and no downloaded code is run. Only in remote mode, `transcribe_server.py` and `translate.py` are copied (`scp`) to `~/.meeting-wingman` on the SSH host you configure and run there with its Python |
| **Runs** | `ffmpeg` (or, with `--app`, PipeWire's `pw-record` and `pw-link`) to record the system audio and microphone, `python3` with faster-whisper (and CTranslate2 for translation) to transcribe, `rsync` and `ssh` only in remote mode. With `--captions`: a DevTools connection to your own browser on `127.0.0.1`, which lists the open tabs to find the meeting and then reads only the caption text of that tab. The browser's permission for that connection covers the whole browser ([what it grants](#what-allow-remote-debugging-grants)) |
| **Sends** | Audio chunks only to the SSH host you configure in `WINGMAN_REMOTE_HOST`, and only if you configure one. Tasks and comments only to the tracker you connected yourself, in team mode, with your confirmation unless you chose `auto`. Transcript lines are read by Claude Code like any other text in your session |
| **Fetches** | The faster-whisper speech model and, with `-x`, the NLLB-200 translation model, from the Hugging Face Hub on first use |
| **Keeps** | Audio chunks for a few seconds, until they are transcribed. The transcript only at the path you give `wingman stop`; no copy is left in the state folder or on the remote host |

No analytics, no telemetry, no server run by the author. Details in [PRIVACY.md](PRIVACY.md).

## FAQ

<details>
<summary><strong>How many tokens does a meeting cost?</strong></summary>

Each event from `wingman watch` is one Claude turn, and every turn re-reads the session's context
(mostly from the prompt cache). So the cost is roughly **number of events × size of the session**,
plus a little output.

Measured on our own meetings (Claude Code, prompt caching on):

| Meeting | Claude turns | Cache reads | Output |
|---|---|---|---|
| 19-minute team sync, filtered events plus ClickUp and Slack work | 115 | 60 M tokens | 44 K tokens |
| 11-minute software sync | 52 | 30 M tokens | 31 K tokens |

Those runs happened inside a long development session of about 500 K tokens, which every turn
re-read. In a fresh session the context is around 30–50 K tokens, so the same meeting reads about
a tenth of that. To keep it low:

- **Start the meeting in a new Claude Code session**, not at the end of a long one.
- Keep the filtered `wingman watch` (not `--raw`): it sends a few events per minute instead of one per sentence.
- Raise `WINGMAN_DIGEST` (seconds between digests of quiet lines) for long meetings.
- Pick a smaller model for the meeting session if the answers are good enough for you.

`/cost` or your usage page shows what a meeting actually used. Transcription and translation run
locally and cost no tokens.
</details>

<details>
<summary><strong>Does the meeting tab have to stay in front?</strong></summary>

No. Chrome stops rendering a tab you are not looking at (another tab in front, the window
minimised, screen sharing), and Meet and Teams then stop updating their captions. The caption
reader keeps the meeting tab rendering while it reads: focus emulation, an "active" page lifecycle
and a 16-pixel screencast, renewed every 30 seconds. On Chrome 156 that took a background tab from
0 to 58 frames per second, the same as a tab in front. The audio source is not affected at all.
</details>

<details>
<summary><strong>Captions or audio?</strong></summary>

Captions when the meeting is in the browser and you want speaker names (team meetings): no GPU,
no audio recorded. Audio for desktop apps, for Zoom, and for languages the platform does not caption.
</details>

<details>
<summary><strong>Does it write to our tracker on its own?</strong></summary>

Only in team mode, and by default it asks first (`confirm`). It comments on an existing task
instead of creating a duplicate, never posts the transcript, does not change statuses unless asked,
and does not touch tasks that have an AI agent assigned (a comment there could start an agent run).
</details>

<details>
<summary><strong>Does a bot join the call?</strong></summary>

No. It only reads what your browser shows or what your computer plays. The other participants see
nothing, which is why the skill reminds you to tell them.
</details>

## Consent and privacy

This tool transcribes other people. In many places you must tell the other participants, or get
their consent, before you do that, and company policies may forbid it. The skill reminds you at the
start; using it lawfully is your responsibility.

Audio and transcripts stay on your machine or your own SSH host. Transcript lines are read by
Claude Code, so they go to the model provider like everything else in your session. See
[PRIVACY.md](PRIVACY.md) for the full policy and [SECURITY.md](SECURITY.md) to report a vulnerability.

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
