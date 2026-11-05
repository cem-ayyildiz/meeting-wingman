# Changelog

## [0.3.1] - 2026-11-05

Fixes from the first real meetings (Meet and Teams team syncs, a Zoom test call).

- Meet: URLs like `meet.google.com/meet/<code>` are recognised; the "Jump to bottom" button text is
  no longer read as a caption.
- Teams: reads the real caption structure of the new Teams web client and follows its virtual list
  (one element reused for another caption); an interim caption and its punctuated final form give
  one line, not two.
- Zoom: the web client runs the meeting in an iframe; captions are read from there. The overlay is
  fragmented, so the docs recommend the audio source for Zoom.
- Captions without final punctuation get twice as long to settle, so slow speech is not cut inside
  a word.
- The reader asks Chrome not to throttle the meeting tab; during screen sharing lines arrived
  minutes late.
- `wingman switch [--meeting TEXT] [OUT.txt]`: save the current meeting and follow another tab on the
  same browser connection, without a new "Allow remote debugging?" prompt.
- "wingman" (as captions spell it: vingman, vincman, ringman, winkman...) wakes Claude in every mode.
- Translation: no more repetition loops ("no, no, no, ...") on short lines.
- Skill rules: never comment on a task that has an AI agent assigned; close duplicates instead of
  deleting; moving between lists may need the UI; no status changes unless asked.
- README: FAQ with measured token costs, captions vs audio, tracker writes; FreshSens uses it in
  its internal meetings.

## [0.3.0] - 2026-11-05

- **Captions source** (`wingman start --captions`): reads the live captions of a Google Meet,
  Microsoft Teams or Zoom web tab over the DevTools protocol, with speaker names, no audio and no
  GPU. Connects to your own browser once (it asks you to allow it) or to a debugging port.
  Meet is tested against its page structure; Teams and Zoom readers are new.
- **Filter** (`wingman watch`): wakes Claude only for questions, the user's name, numbers
  (coach mode) or commitments, decisions, blockers, dates (team mode), with the quiet lines before
  it as context and a digest of the rest every 5 minutes. With captions it knows the user's own
  lines. `wingman watch --raw` gives every line.
- **Cut at pauses**: a voice-activity segmenter replaces the fixed 20-second chunks. A line now
  arrives 1–3 s after the speaker pauses instead of 20–25 s, and silence is never transcribed.
- **Pick the meeting**: `--app zoom|teams|chrome ...` records only that application's audio
  (PipeWire; the app keeps playing to the speakers), `--captions --meeting "<title>"` reads one tab
  when several are open, and `wingman meetings` lists the apps playing audio and the meeting tabs.
  README has a use-case table (client call, standup, two meetings, late join, switching,
  translation, interview, webinar, phone dial-in, GPU box).
- **Microphone recorded by default** together with the system audio (`--no-mic` to leave it out).
- `wingman doctor` checks the setup; `wingman show N` prints recent lines; `wingman level` measures
  system audio and microphone separately; `wingman stop` waits for the last utterance.
- Tests for the filter, the segmenter and the caption reader (including an end-to-end run against a
  mock Meet page in headless Chrome) run in CI.
- README: the two sources, VS Code as the recommended place to run it, new diagram.

## [0.2.1] - 2026-11-05

- `wingman stop` keeps no copy of the meeting behind: the local transcript is moved to the path you
  give, and the copy on the remote host is deleted once it has been fetched. Leftover chunks and the
  term list are removed too.
- `bin/wingman` puts the command on the PATH inside Claude Code and marks the plugin as Claude Code only.
- PRIVACY.md, SECURITY.md, plugin icon, example prompts, and a README section on everything the
  plugin runs, sends and fetches.

## [0.2.0] - 2026-11-05

- **Team mode**: action items and decisions heard in the meeting become new tasks or comments on
  existing tasks in the connected tracker (ClickUp, Linear, Jira, GitHub Issues, Asana ...), with
  `confirm`, `auto` or `end` write policies, owner matching and duplicate checks.
- **Translation**: `wingman start -x <language>` adds a translated line under each line, using a
  local NLLB-200 model through CTranslate2 (no new dependencies).
- **GPU to CPU fallback** inside the transcriber and the translator: a missing, busy or
  out-of-memory GPU no longer stops the start, it loads on the CPU and says so.
- README: coach and team modes, Meet/Teams/Zoom support, translation.

## [0.1.1] - 2026-11-05

- README rewritten: demo image, pipeline diagram, limits, troubleshooting.
- CI (shellcheck, Python syntax, manifest and version checks), contributing guide, issue template.

## [0.1.0] - 2026-11-05

First public release.

- `wingman` command: `start`, `watch`, `stop`, `level`, `status`.
- Local transcription by default (`large-v3` on GPU, `small` on CPU); optional remote GPU over SSH.
- Falls back to local transcription when SSH fails or the remote model does not load.
- Linux capture through PulseAudio/PipeWire; macOS through a loopback device (beta).

Lessons that are built in:

- Whisper invents sentences during silence ("Thank you for watching", subtitle credits, the hint
  list read back). The server filters them; Turkish `İ`/`ı` are normalised before matching.
- `condition_on_previous_text` made the model repeat the previous sentence for minutes on muffled
  audio. It is off.
- Chunks are ordered by name, not modification time, and leftovers are cleared on start;
  otherwise half-written chunks were shipped.
- `pkill -f` over SSH killed its own remote shell. PID files are used instead.
- Long jobs started from an agent's background shell can be killed at a time limit. Everything
  runs under `setsid`.
