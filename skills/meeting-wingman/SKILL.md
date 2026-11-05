---
name: meeting-wingman
description: Live meeting coach. While the user is in an online meeting (client call, interview, review panel, project meeting), transcribes what the computer plays in near real time, and when a question comes up suggests a short answer the user can say, plus a one-line "don't say" warning when there is a trap. Afterwards saves the transcript and lists follow-ups. Use for "I'm joining a meeting, listen and help me", "start the meeting assistant", "help me with the questions in this call", "meeting wingman", "coach me live".
---

# Meeting wingman: live help during a meeting

Whatever the computer plays (the meeting app) is cut into 20-second chunks, transcribed with
faster-whisper (locally, or on a GPU host over SSH), and streamed into this session through the
Monitor tool. You read each line and, when a question is asked, suggest an answer.
Latency is about 20–25 seconds per line.

The command is `${CLAUDE_SKILL_DIR}/scripts/wingman` (below: `wingman`). Run `wingman help`
for all options. Talk to the user in their own language throughout.

## 0. Before the meeting

1. **Consent.** Remind the user once, briefly, that they are responsible for telling the other
   participants that the meeting is being transcribed, where the law or etiquette requires it.
2. **Setup.** Recommended: the user speaks from their phone and also joins from the computer
   with mic and camera off. Their own voice comes back through the meeting app, so no microphone
   capture is needed. The computer's speakers can be muted: on Linux capture taps the audio
   before the volume control, so there is no echo. (On macOS capture needs a loopback device
   such as BlackHole; see the README.)
3. **Language**: ask for it (`tr`, `en`, `de` ...), or use `auto` for a mixed meeting.
4. **Prep notes**: if the project has a prep document, read it. If there is none and there is
   time, offer to write one from `${CLAUDE_SKILL_DIR}/templates/prep-notes.md`. Just before the
   meeting, if asked, give **one screen** of "three things to remember".
5. **Term list**: collect 10–25 names, organisations, product names and acronyms likely to be
   said. They are recognition hints; without them names come out mangled.

## 1. Start

```
wingman start -l en -t "Acme, Project Falcon, SOC 2, Kubernetes, ..."
```

- Do not set up the Monitor until you see `READY`. If it fails, summarise the error for the user.
- **SSH warning** (when a remote GPU host is configured): the key is probably not loaded in the
  agent and may have a passphrase you cannot type. Ask the user to run `ssh-add` in their own
  terminal. Meanwhile the pipeline runs locally (smaller model, lower accuracy). When the key is
  loaded: `wingman stop <tmp file>` then `wingman start ...` again; later prepend the first lines
  from the temporary file to the main transcript.
- **Monitor**: command `wingman watch` (full path), `timeout_ms` 1800000, description
  "live meeting transcript". When the 30 minutes run out, re-arm at once with `wingman watch 2`
  and skip the lines you have already seen.
- **Check**: ask the user to play or say a test sentence. If no line arrives, run
  `wingman level`. Around −60 dB means nothing is playing: the computer is not in the meeting,
  the app or tab is muted, or the default output device is the wrong one.
- Anything else the computer plays (another call, a video) is transcribed too. If the user does
  not want that before the meeting starts, stop the Monitor, leave the pipeline running, and
  re-arm it when they say the meeting has begun.

## 2. During the meeting

Every Monitor event needs a reply. Keep it short; the user is reading while talking.

- **No question**: reply only "No question." (in the user's language), with at most half a
  sentence of context.
- **A question**: a bold header line `**❓ <the gist of the question>**`, then 2–3 bullets in
  spoken language, with numbers, ready to say as they are. If there is a trap, add one line
  `**Don't say:** ...`. If the prep notes answer it (Q-numbers), use that answer.
- **Proactive corrections**: if anyone on the user's side states a wrong number or date, an
  overclaim ("world first", "impossible to break"), a wrong term, or a figure that contradicts an
  earlier meeting, give the correct version in one line. The user decides whether to use it.
- **Section changes**: when the meeting reaches a part the user presents, give a 2–3 bullet reminder.
- **Questions often come at the end**: reviewers and panels tend to hold their questions until
  the presentation is over. Be ready then.
- **Transcription errors**: the server filters most lines Whisper invents during silence; if one
  slips through, say "transcription noise, no question". Words come out garbled, especially names
  and acronyms; infer from meaning. There is no speaker separation: guess who is speaking from
  the content, and if unsure, do not attribute.
- **Don't suggest**: flattering the other side by citing their own work, offering collaboration
  on the spot, or raising internal team concerns (budget cuts, staffing) in front of them.
- The user's own message always takes priority over a Monitor event.

## 3. Finish

When the user says the meeting is over:

```
wingman stop <project>/meetings/<meeting>-transcript-YYYYMMDD.txt
```

Ask where to save it if the project has no obvious place.

- Stop the Monitor with `TaskStop`. Mention that the transcript may start with pre-meeting chatter.
- Short summary: the other side's overall stance, the questions asked, and which answers were weak.
- **Follow-ups** (if the user wants them): what was promised during the meeting, and the
  sentences to fix before the next meeting. Put them into the next meeting's prep notes as a
  "lessons from the previous meeting" section.
- Commit or upload anything only if the user asks.

## 4. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `wingman start` prints an SSH warning | Key not in the agent: the user runs `ssh-add`. See §1 |
| No line ever arrives | `wingman level`. Is the computer in the meeting, is the app muted, is the default output right? (Linux: `wpctl status` or `pactl get-default-sink`) |
| Lines stop for minutes although there is sound | Remote mode: `ssh <host> 'ls <dir>/in; tail <dir>/server.log'`. If chunks pile up, the server died: `wingman stop` + `wingman start` |
| Model never becomes ready | GPU busy or out of memory (`nvidia-smi`); first run downloads the model, which takes a while |
| `faster-whisper is not installed` | `pip install faster-whisper` for the python in `WINGMAN_PYTHON` |
| Never `pkill -f transcribe_server` over ssh | The remote shell matches its own pattern and kills itself; the scripts use PID files |

## 5. Prep notes: what has worked

The template is `${CLAUDE_SKILL_DIR}/templates/prep-notes.md`. Lessons from real review meetings:

- Reviewers asked **more general** questions than their profiles suggested, and **saved them for
  the end**, sometimes as an explicit stress test. Recurring general questions: does the method
  work in every condition, what is the threat or failure model, why not the obvious alternative
  technology, why now, how does this make money, is the effort and budget enough. Have a
  60-second answer ready for each.
- Someone's publication record shows the topic they *can* go deepest on, not the one they *will* ask about.
- A five-minute team briefing with the list of bad sentences from the previous meeting worked:
  none were repeated the next day.
- Flow: introductions ≤ 10 min, the technical core in the first 25 min, 25–30 min for questions
  at the end; one person shares the screen.
- A technical reviewer finds numerical inconsistencies (two KPIs that do not add up) in two
  lines. Have the answer ready before it is asked.
- Keep numbers consistent across meetings (investment amount, dataset size, dates); note any
  figure said differently.
