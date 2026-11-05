---
name: meeting-wingman
description: Live meeting wingman for Google Meet, Microsoft Teams, Zoom or any call. Follows the meeting in near real time, from the system audio or from the meeting's own captions in the browser (with speaker names), can translate it, wakes up only for lines that matter, and then either coaches the user (suggests a short answer when a question comes up, warns what not to say) or works the meeting like a teammate (turns action items and decisions into tasks in the connected tracker such as ClickUp, Linear, Jira, GitHub or Asana, or adds them as comments on existing tasks). Afterwards saves the transcript and lists follow-ups. Use for "I'm joining a meeting, listen and help me", "start the meeting assistant", "help me with the questions in this call", "take the action items from our standup into ClickUp", "meeting wingman", "coach me live", "translate this call for me".
---

# Meeting wingman

Two ways to follow a Meet, Teams or Zoom call:

- **Audio** (default, works with any app, desktop or browser): the system audio and the
  microphone are cut at speech pauses and transcribed with faster-whisper, on a GPU when one is
  usable and on the CPU otherwise, locally or on a GPU host over SSH. A line arrives 1–3 seconds
  after the speaker pauses. No speaker names.
- **Captions** (`--captions`, the meeting open in Chrome, Edge or Chromium): the meeting's own live
  captions are read from the browser tab. Speaker names included, no GPU, no audio recorded.
  Best for team mode, where knowing who said "I'll do it" matters.

A local filter (`wingman watch`) wakes you only for lines that matter: questions, the user's name,
commitments, decisions, blockers, dates and numbers, depending on the mode. Everything else
arrives as a digest every few minutes, so you keep up with the meeting without a reply per sentence.

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
2. **Setup.** First time on a machine, run `wingman doctor` and fix what it marks ✗.
   - Recommend running Claude Code in **VS Code** (or another editor with the Claude Code panel)
     next to the meeting window: the replies stay readable beside the call.
   - **Audio source**: the user joins from the computer as usual; the system audio and the default
     microphone are both recorded. If they speak from another device (a phone dialled into the
     same meeting), add `--no-mic`, because their voice already comes back through the meeting app.
     On macOS system audio needs a loopback device such as BlackHole.
   - **Captions source**: the meeting must be open in the browser (not the desktop app) with
     captions turned on (CC), in the meeting's language. Remote debugging must be on once:
     `chrome://inspect/#remote-debugging` (or `edge://inspect`). When `wingman start --captions`
     connects, the browser asks "Allow remote debugging?": tell the user to click Allow. If the
     user prefers a separate browser, `--cdp <port>` with a browser started with
     `--remote-debugging-port=<port>`.
   - Pick captions when the meeting runs in the browser and speaker names help (team mode); pick
     audio for desktop apps, or when captions are not available in the meeting's language.
3. **Languages.** The meeting language (`-l tr`, `-l en` ..., or `-l auto` for a mixed meeting).
   If the user wants every line translated as well, add `-x <language>`: a translated line
   appears under each original line, computed on the GPU or CPU by a local NLLB model (first run
   downloads it, about 0.6 GB). You can also translate in your own replies without `-x`.
4. **Term list** (audio source). 10–25 names, organisations, product names and acronyms likely to
   be said. They are recognition hints; without them names come out mangled. In team mode, take
   the names of the team members from the tracker.
5. **The user's name(s)** for `-n`, so "Ana, what do you think?" wakes you. Include short forms.
6. **Coach mode:** if the project has prep notes, read them. If not and there is time, offer to
   write them from `${CLAUDE_SKILL_DIR}/templates/prep-notes.md`. Just before the meeting, if
   asked, give **one screen** of "three things to remember".
7. **Team mode:** see §3a.

## 1. Pick the meeting, then start

Start as soon as the user asks, also when the meeting is already running; preparation can
happen while it runs. Map what the user says to a target:

| User says | Target |
|---|---|
| "the Zoom call", "Teams", "the one in Chrome" (a desktop app or one browser) | audio with `--app zoom` / `--app teams` / `--app chrome` |
| "the Meet", a meeting title or code, and the meeting is in the browser | `--captions` (add `--meeting "<title or code>"` if several are open) |
| nothing specific, one meeting running | audio from everything (default), or captions if a meeting tab is open |
| unclear, or several meetings | run `wingman meetings` and ask which one, naming what it lists |
| "switch to the other call" | captions: `wingman switch --meeting "<title or code>" <file for this one>` (same browser connection, no new approval); audio: `wingman stop <file>`, then `wingman start` with the new target |

`--app` needs PipeWire (most current Linux desktops); `wingman meetings` shows the app names that
are playing audio. Captions need the meeting in the browser with captions turned on.

Per platform, from real meetings: **Meet** and **Teams** (web) captions work well and give speaker
names; on Teams the user's own lines carry their full name, not "You", so pass it with `-n`.
**Zoom**'s caption overlay comes in fragments and without names: for Zoom prefer the audio source
(`--app chrome` or `--app zoom`), or ask the host to turn on Zoom's full transcript.

**Cost:** every event is one Claude turn that re-reads the whole session. Suggest starting the
meeting in a fresh session (not in a long working session), keep the filtered `wingman watch`, and
for long meetings a larger `WINGMAN_DIGEST`.

### Start

```
wingman start -m coach -n "Ana" -l en -t "Acme, Project Falcon, SOC 2, ..."   # client call, audio
wingman start -m team -n "Ana" --captions                                     # team sync in Meet
wingman start -m coach -l ja -x en                                            # Japanese call, English under each line
```

`-m` sets what wakes you: `coach` (questions, the user's name, numbers), `team` (commitments,
decisions, blockers, dates, the user's name) or `both`.

- Do not set up the Monitor until you see `READY`. If it fails, summarise the error for the user.
  `READY` names the model and device; if the GPU was busy it says `cpu` and accuracy is lower.
  Tell the user in one line.
- **SSH warning** (when a remote GPU host is configured): the key is probably not loaded in the
  agent and may have a passphrase you cannot type. Ask the user to run `ssh-add` in their own
  terminal. Meanwhile the pipeline runs locally. When the key is loaded: `wingman stop <tmp file>`
  then `wingman start ...` again; later prepend the lines from the temporary file to the transcript.
- **Monitor**: command `wingman watch` (full path), `timeout_ms` 1800000, description
  "live meeting transcript". When the 30 minutes run out, re-arm at once with `wingman watch 2`
  and skip what you have already seen.
- **Events** from `wingman watch`:
  - `▶ question, name · 14:02:33` followed by the trigger line and, marked `…`, the quiet lines
    since the previous event. Act on it (§2, §3).
  - `◇ digest 14:00:10–14:05:02 · 12 lines, no trigger`: the meeting moved on with nothing for
    you. Read it for context and reply with at most one short line (or "—"); speak up only if
    something in it needs the user (a wrong number, a missed commitment).
  - `▶ wingman · …`: someone in the meeting is talking to you ("wingman, add a comment", spelled
    vingman / vincman / ringman by the captions). Do what is asked, within the rules below, and
    answer in one line; the user may read it out.
  - Need more context? `wingman show 60` prints the last 60 lines.
- **Check**: ask the user to say a test sentence (audio) or to check that captions are on
  (captions). If nothing arrives, run `wingman level` (audio): around −60 dB means silence, the
  computer is not in the meeting, the app is muted, or the wrong device is selected.
  `wingman status` shows what is running.
- Anything else the computer plays (another call, a video) is transcribed too. If the user does
  not want that before the meeting starts, stop the Monitor, leave the pipeline running, and
  re-arm it when they say the meeting has begun.

## 2. During the meeting: coach mode

Keep every reply short; the user is reading while talking.

- **A trigger that is not really a question for the user** (a rhetorical question, the user's
  own question): reply "—" or one line at most.
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
- **Owners.** Assign only people who are members of the workspace, matched by name. With the
  captions source each line starts with the speaker's name ("You" is the user), so "I'll do it"
  has an owner. With the audio source there are no speaker names: infer from context, and if
  unsure, leave it unassigned and ask the user.
- **Content.** Short, factual, in the workspace's language. Add one line:
  "From <meeting name>, <date> ~<time>". Never paste the full transcript or long quotes into
  the tracker, and never post what was said in confidence or off topic.
- **Speed over polish.** In `confirm` mode, propose as soon as an item is clear; the user
  answers in a word while the meeting goes on.
- After every write, reply with the link in one line.
- **Agents on tasks.** Before commenting on or changing a task, check its assignees. If an AI agent
  is assigned (for example "Agent Multica"), a new comment or status change can start an agent run:
  do not write there; say so and offer to remove the agent first (with the user's or task owner's
  go-ahead), or to write elsewhere.
- **Close, don't delete.** Asked to remove a duplicate, close it (or mark it done) instead of
  deleting; deleting through the API is permanent.
- **Moving between lists** (backlog to sprint) is often not possible through the API; if it fails,
  say so and ask the owner to drag it in the UI.
- Never change a task's status unless asked; reassigning, closing and moving are separate requests.

## 4. Both modes

- **Transcription errors** (audio): silence is never transcribed and the server filters the
  phrases Whisper tends to invent; if one slips through, say "transcription noise". Words come out
  garbled, especially names and acronyms; infer from meaning. If you are unsure who is speaking,
  do not attribute. Captions have their own errors, and the platform may rewrite the last words
  of a caption; lines are emitted once a caption has settled.
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
| First run on a machine | `wingman doctor`: ffmpeg, faster-whisper, GPU, audio levels, microphone, SSH host, browser debugging |
| `--captions` fails to connect | Remote debugging is off (`chrome://inspect/#remote-debugging`), or the user did not click Allow. Each `wingman start --captions` asks once |
| `--app` records nothing | The app has not played sound yet, or its name differs: `wingman meetings` lists the names; the match is a case-insensitive regex |
| `--captions` lines arrive minutes late while screen sharing | The reader asks Chrome not to throttle the tab; if it still happens, keep the meeting window visible |
| Zoom captions arrive in fragments | Zoom's overlay rolls word groups; use the audio source for Zoom |
| `--captions` reads the wrong meeting | Several meeting tabs are open: `--meeting "<title or code>"` |
| `--captions` says no captions on the page | Captions (CC) are off in the meeting, or the meeting runs in the desktop app; use the audio source instead |
| A Bluetooth headset sounds worse after start | Opening its microphone switches it to headset mode. In a call the app already does this; otherwise use `--no-mic` |
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
