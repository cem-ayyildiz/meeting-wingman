# Privacy policy

Last updated: 2026-11-06 (0.3.3)

meeting-wingman is open-source software that runs on your own computer inside Claude Code. The
author does not operate any server for it, does not receive any of your data, and collects no
analytics or telemetry.

## What the plugin handles

| Data | Where it goes | How long it is kept |
|---|---|---|
| Audio during a meeting: what the computer plays and, unless you turn it off with `--no-mic`, your microphone (the voices of you and the other participants) | Cut by `ffmpeg` and a local segmenter into one WAV file per utterance on your computer; silence is not kept. With `--app`, only that application's audio is recorded, through PipeWire links that are removed when recording stops; your audio routing is not changed. In remote mode, copied over SSH (`rsync`) to the host **you** configure in `WINGMAN_REMOTE_HOST`, nowhere else | Each chunk is deleted as soon as it is transcribed, usually within seconds. `wingman stop` deletes any chunk left over |
| The transcript (and translation, with `-x`) | Written to a file on your computer, or on your remote host while the meeting runs | On the remote host it is deleted after `wingman stop` fetches it. Locally `wingman stop` moves it to the path you choose and keeps no other copy. You decide how long to keep that file |
| Captions, with `--captions` | Read from the meeting tab of your own browser over a local DevTools connection (`127.0.0.1`). To find the meeting tab it lists the addresses and titles of the open tabs; from the meeting tab it then reads only the caption text and speaker names. No other page content, cookie or password is read, and nothing is sent anywhere. To keep a background tab updating its captions it asks that tab for a 16×16-pixel screencast; those frames are acknowledged and discarded, never decoded or saved. **Note:** the permission the browser asks for ("Allow remote debugging") is broader than what the plugin uses: it gives the connection control of the whole browser. Switch remote debugging off after the meeting, or use a separate browser profile with `--cdp <port>`; see [the README](README.md#what-allow-remote-debugging-grants) | Written to the transcript like audio lines, with the same retention |
| Recognition hints (`-t` term list) | A small text file next to the transcriber | Deleted by `wingman stop` |
| Transcript lines read by Claude | Your Claude Code session, which sends them to the model provider like any other text in the session | Under the provider's terms for your account |
| Tasks and comments in team mode | The task tracker **you** have connected to Claude Code (for example ClickUp, Linear, Jira, GitHub, Asana), through that tracker's own MCP server or CLI, only when you confirm or turn on `auto` | Under that tracker's terms. The plugin never writes the full transcript into a tracker |

## What the plugin downloads

On first use, the speech model (faster-whisper) and, with `-x`, the translation model (NLLB-200)
are downloaded from the Hugging Face Hub (`huggingface.co`) into your local Hugging Face cache.
No meeting data is sent to Hugging Face; the request is an ordinary file download.

## What the plugin does not do

- It does not join meetings as a bot and does not use any meeting platform's API.
- It does not send audio or text to any service the author runs, or to any service you have not
  configured yourself.
- It does not store conversation content to build profiles, and it does not read credentials
  from your environment.

## Other people's privacy

The plugin transcribes other people. In many places you must tell them, or get their consent,
before you do that. The skill reminds you at the start of every meeting; complying with the law
and your organisation's policies is your responsibility.

## Children

meeting-wingman is not intended for people under 18.

## Contact

Questions about this policy: open an issue at
https://github.com/cem-ayyildiz/meeting-wingman/issues. Security problems: see [SECURITY.md](SECURITY.md).
