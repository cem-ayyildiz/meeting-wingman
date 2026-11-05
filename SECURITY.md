# Security policy

## Reporting a vulnerability

Please report security problems privately through GitHub:
**[Report a vulnerability](https://github.com/cem-ayyildiz/meeting-wingman/security/advisories/new)**
(Security tab → "Report a vulnerability"). Do not open a public issue for them.

Expect a first answer within a week. Fixes are released as a new version and noted in
[CHANGELOG.md](CHANGELOG.md).

## Supported versions

Only the latest release on `main` receives fixes.

## Scope

In scope: anything in this repository, for example a way to make `wingman` send audio or
transcripts anywhere other than the configured host, run unexpected code, or leave meeting data
behind after `wingman stop`.

Out of scope: vulnerabilities in ffmpeg, faster-whisper, CTranslate2, the Hugging Face Hub,
Claude Code, or the task trackers you connect. Please report those to their projects.
