## What this changes

<!-- One or two sentences, and the issue it closes, if any (Closes #123). -->

## How you tested it

<!-- A real run if the change touches capture, transcription or captions:
     platform, OS, audio stack, source (--captions or audio). -->

## Checklist

- [ ] `shellcheck skills/meeting-wingman/scripts/wingman`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `claude plugin validate .`
- [ ] After `wingman stop`, no `transcribe_server`, `ffmpeg` or caption reader process is left
- [ ] README, PRIVACY or SKILL.md updated if the change alters what runs, what is sent or what is kept
- [ ] No names or private content from real meetings in tests, fixtures or logs
