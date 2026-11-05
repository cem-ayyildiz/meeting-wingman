---
name: meeting-wingman
description: Live meeting wingman for Google Meet, Microsoft Teams, Zoom or any call. Transcribes the meeting in near real time (and can translate it), then either coaches the user (suggests a short answer when a question comes up, warns what not to say) or works the meeting like a teammate (turns action items and decisions into tasks in the connected tracker such as ClickUp, Linear, Jira, GitHub or Asana, or adds them as comments on existing tasks). Afterwards saves the transcript and lists follow-ups. Use for "I'm joining a meeting, listen and help me", "start the meeting assistant", "help me with the questions in this call", "take the action items from our standup into ClickUp", "meeting wingman", "coach me live", "translate this call for me".
---

# Meeting wingman

Whatever the computer plays (the Meet, Teams or Zoom window, desktop app or browser) is cut into
20-second chunks and transcribed with faster-whisper: on a GPU when one is usable, otherwise on
the CPU, locally or on a GPU host over SSH. Lines stream into this session through the Monitor
tool. Latency is about 20–25 seconds per line.

The command is `${CLAUDE_SKILL_DIR}/scripts/wingman` (below: `wingman`). `wingman help` lists
every option. Talk to the user in their own language throughout.

There are two modes. Ask which one, or infer it from the request; both can run at once.

| Mode | For | What you do with each line |
|---|---|---|
| **coach** | Meetings where the user must answer: clients, interviews, reviews, investors | Suggest answers to questions, flag traps and wrong numbers |
| **team** | Internal meetings: standups, planning, project syncs | Capture action items and decisions into the task tracker |

## 0. Before the meeting

1. **Consent.** Remind the user once, briefly, that they are responsible for telling the other
   participants that the meeting is being transcribed, where the law or etiquette requires it.
2. **Setup.** Recommended: the user speaks from their phone and also joins from the computer
   with mic and camera off. Their own voice comes back through the meeting app, so no microphone
   capture is needed, and the computer's speakers can be muted (on Linux capture taps the audio
   before the volume control). If they join only from the computer, set `WINGMAN_MIC` so their
   own voice is captured too. On macOS capture needs a loopback device such as BlackHole.
3. **Languages.** The meeting language (`-l tr`, `-l en` ..., or `-l auto` for a mixed meeting).
   If the user wants every line translated as well, add `-x <language>`: a translated line
   appears under each original line, computed on the GPU or CPU by a local NLLB model (first run
   downloads it, about 0.6 GB). You can also translate in your own replies without `-x`.
4. **Term list.** 10–25 names, organisations, product names and acronyms likely to be said.
   They are recognition hints; without them names come out mangled. In team mode, take the
   names of the team members from the tracker.
5. **Coach mode:** if the project has prep notes, read them. If not and there is time, offer to
   write them from `${CLAUDE_SKILL_DIR}/templates/prep-notes.md`. Just before the meeting, if
   asked, give **one screen** of "three things to remember".
6. **Team mode:** see §3a.

## 1. Start

```
wingman start -l en -t "Acme, Project Falcon, SOC 2, Kubernetes, ..."
wingman start -l ja -x en -t "..."      # Japanese meeting, English translation under each line
```

- Do not set up the Monitor until you see `READY`. If it fails, summarise the error for the user.
  `READY` names the model and device; if the GPU was busy it says `cpu` and accuracy is lower.
  Tell the user in one line.
- **SSH warning** (when a remote GPU host is configured): the key is probably not loaded in the
  agent and may have a passphrase you cannot type. Ask the user to run `ssh-add` in their own
  terminal. Meanwhile the pipeline runs locally. When the key is loaded: `wingman stop <tmp file>`
  then `wingman start ...` again; later prepend the lines from the temporary file to the transcript.
- **Monitor**: command `wingman watch` (full path), `timeout_ms` 1800000, description
  "live meeting transcript". When the 30 minutes run out, re-arm at once with `wingman watch 2`
  and skip the lines you have already seen.
- **Check**: ask the user to play or say a test sentence. If no line arrives, run
  `wingman level`. Around −60 dB means nothing is playing: the computer is not in the meeting,
  the app or tab is muted, or the default output device is the wrong one.
- Anything else the computer plays (another call, a video) is transcribed too. If the user does
  not want that before the meeting starts, stop the Monitor, leave the pipeline running, and
  re-arm it when they say the meeting has begun.

## 2. During the meeting: coach mode

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
- **Hard questions often come at the end**, after the presentation. Be ready then.
- **Don't suggest**: flattering the other side by citing their own work, offering collaboration
  on the spot, or raising internal team concerns (budget cuts, staffing) in front of them.

## 3. During the meeting: team mode

### 3a. Setup (before or at the start)

1. **Tracker.** Use whichever task tracker is connected as an MCP server or CLI (ClickUp, Linear,
   Jira, GitHub Issues, Asana, Notion ...). If several are, ask. If none is, say so and collect the
   items in a file instead.
2. **Where.** Ask for the list, project or board the meeting belongs to. Load its members (to
   match owners) and its open tasks (to match topics to existing tasks). Keep both in context.
3. **Write policy.** Ask once, default `confirm`:
   - `confirm`: propose each item; write it when the user answers "ok", "1", "yes" or similar.
   - `auto`: write at once and report the link. Only when the user explicitly asks for it.
   - `end`: collect everything and write it all after the meeting, once the user has reviewed the list.
4. **Conventions.** Follow the workspace's conventions (language, title style, tags, statuses).
   If the user has rules about the tracker (for example "everything in English"), they apply.

### 3b. What to capture

| Heard | Proposal |
|---|---|
| A commitment: "I'll send the draft by Friday", "can you check the logs?" | **New task**: title, owner, due date if said |
| News about something that already has a task: progress, a blocker, a changed date | **Comment** on that task |
| A decision: "we go with option B" | **Comment** on the related task, or a decision note if there is none |
| A problem nobody owns yet | **New task**, unassigned, flagged as such |

Reply format, one item per block:

```
📌 New task · <list>
<title>
Owner: <name> · Due: <date or "not said">
> "<the sentence it came from>"   [14:02]
```

```
💬 Comment · <task name> (<id>)
<one or two sentences: what changed>
```

Other Monitor events get "No action item." or nothing at all if the user asked for quiet.

### 3c. Rules

- **Check before creating.** If an open task matches, propose a comment instead of a duplicate.
  Never propose the same item twice in one meeting; update the earlier proposal instead.
- **Owners.** Assign only people who are members of the workspace, matched by name. If the
  transcript is unclear about who, leave it unassigned and say so. There is no speaker
  separation: "I'll do it" needs context to know who "I" is; if unsure, ask the user.
- **Content.** Short, factual, in the workspace's language. Add one line:
  "From <meeting name>, <date> ~<time>". Never paste the full transcript or long quotes into
  the tracker, and never post what was said in confidence or off topic.
- **Speed over polish.** In `confirm` mode, propose as soon as an item is clear; the user
  answers in a word while the meeting goes on.
- After every write, reply with the link in one line.

## 4. Both modes

- **Transcription errors**: the server filters most lines Whisper invents during silence; if one
  slips through, say "transcription noise". Words come out garbled, especially names and
  acronyms; infer from meaning. If you are unsure who is speaking, do not attribute.
- With `-x`, translated lines start with `↳ <language>:`. Use the original for meaning and
  numbers; the translation is for the user.
- The user's own message always takes priority over a Monitor event.

## 5. Finish

When the user says the meeting is over:

```
wingman stop <project>/meetings/<meeting>-transcript-YYYYMMDD.txt
```

Ask where to save it if the project has no obvious place.

- Stop the Monitor with `TaskStop`. Mention that the transcript may start with pre-meeting chatter.
- **Coach mode**: short summary: the other side's overall stance, the questions asked, which
  answers were weak, and what was promised. Offer to add "lessons from this meeting" to the next
  meeting's prep notes.
- **Team mode**: a table of everything written (task or comment, title, owner, link) and the
  proposals that were not confirmed. In `end` mode, show the list, let the user edit it, then write.
- Commit, upload or share anything only if the user asks.

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `wingman start` prints an SSH warning | Key not in the agent: the user runs `ssh-add`. See §1 |
| `READY` says `cpu` although there is a GPU | GPU busy or out of memory; it fell back on purpose. `nvidia-smi` shows who holds it |
| No line ever arrives | `wingman level`. Is the computer in the meeting, is the app muted, is the default output right? (Linux: `wpctl status`) |
| Lines stop for minutes although there is sound | Remote mode: `ssh <host> 'ls <dir>/in; tail <dir>/server.log'`. If chunks pile up, the server died: `wingman stop` + `wingman start` |
| `faster-whisper is not installed` | `pip install faster-whisper` for the python in `WINGMAN_PYTHON` |
| Never `pkill -f transcribe_server` over ssh | The remote shell matches its own pattern and kills itself; the scripts use PID files |

## 7. Prep notes (coach mode)

Template: `${CLAUDE_SKILL_DIR}/templates/prep-notes.md`. What tends to matter:

- People ask **more general** questions than their background suggests, and often **save them
  for the end**. Have a 60-second answer ready for the classics: does it work in every condition,
  what is the failure or threat model, why not the obvious alternative, why now, how does it make
  money, is the effort and budget enough.
- Someone's track record shows the topic they *can* go deepest on, not the one they *will* ask about.
- Before a follow-up meeting, a five-minute team briefing on the sentences that went badly last
  time keeps them from being repeated.
- Numerical inconsistencies (two figures that do not add up) are found quickly by technical
  people. Have the answer ready before it is asked.
- Keep numbers consistent across meetings; note any figure said differently.
