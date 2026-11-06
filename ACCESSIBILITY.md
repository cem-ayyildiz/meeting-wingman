# Accessibility

meeting-wingman should be usable by anyone who uses Claude Code, including people who rely on a
screen reader, keyboard-only input or captions. If something gets in your way, please tell us
(see [Reporting a barrier](#reporting-a-barrier)).

## How it works for you

- **Everything is text.** The plugin has no graphical interface of its own. The live transcript,
  Claude's answer cards and the task proposals are plain text and Markdown in the Claude Code
  terminal or editor panel. They work with the screen reader, font size, zoom and colour theme
  you already use there.
- **Keyboard only.** Every step is a typed command (`wingman start`, `wingman stop` ...) or a
  short typed answer to Claude ("ok", "1"). No step needs a mouse, except clicking **Allow** in
  the browser once per `--captions` session.
- **Meaning never rests on colour or symbols alone.** Answer cards begin with ❓ followed by the
  question in words; `wingman doctor` writes ✓, ✗ and ! next to a sentence that says what is
  wrong and how to fix it.
- **A written record of the meeting.** The transcript, with speaker names from the captions
  source and an optional translated line under each line (`-x`), is saved as a plain text file.
  Some people find this useful for following a meeting, reviewing it afterwards or reading it in
  their own language.
- **Images in the docs have text alternatives.** Each diagram and screenshot in the README has
  alt text that describes what it shows.

## Supported environments

- Claude Code in a terminal, or in VS Code and other editors with the Claude Code panel.
- Linux (PulseAudio or PipeWire) is tested most. macOS works with a loopback device such as
  BlackHole but is tested less. Windows audio capture is not supported yet. The captions source
  works wherever Chrome, Edge or Chromium runs.
- Google Meet and Microsoft Teams in the browser for captions; any meeting app for audio.

## Known limitations

- **Not a certified captioning service.** Transcription and translation make mistakes, especially
  with names, acronyms, accents and overlapping speech. The text arrives 1–3 seconds after
  speech. Do not rely on it where accurate captions are a legal or safety requirement.
- **Replies come fast during a meeting.** Coach mode keeps each reply to a few lines, but a busy
  meeting can still produce several in a row. A screen reader may read them while you are
  listening to the call. You can ask Claude to stay quieter (for example, only questions
  addressed to you by name), or review the transcript afterwards.
- **The audio source has no speaker names**, and Zoom's web captions arrive in fragments without
  names. Use Meet or Teams captions when you need to know who said what.
- **No spoken output.** The plugin does not read answers aloud.
- The browser's "Allow remote debugging" dialog and `chrome://inspect` are Chrome's own pages;
  their accessibility depends on the browser.

## Reporting a barrier

Open an issue with the label `accessibility`, or email cem.ayyildiz@gmail.com if you prefer not
to report it publicly. Say what you were trying to do, what got in the way, and which assistive
technology, editor and operating system you use. Expect a first answer within a week.
