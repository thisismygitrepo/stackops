# Handover

Use `handover` when the user asks to transfer current work to a new interactive agent instance. Read [herdr.md](herdr.md) first.

Start a normal external agent through `herdr`, not an internal subagent. Use a fresh Herdr tab with one pane. Split into panes only when the user explicitly asks for pane-based handover.

## Protocol

1. Inspect `herdr --help` and relevant tab/pane/agent help.
2. Identify the current interactive agent executable from the process tree:
   - `codex` hands over to `codex`
   - `opencode` hands over to `opencode`
   - `pi` hands over to `pi`
   - another CLI hands over to the same executable
3. Gather fresh context: cwd, branch, git status, changed files, task tracker state, commands run, outcomes, blockers, and next steps.
4. Write the handoff packet using the format below.
5. Launch the new agent with the autonomous argv from [herdr.md](herdr.md), in the current cwd unless the user asks otherwise.
6. Submit a short Herdr prompt that points to the handoff packet, send explicit `Enter` to the target pane, and verify the agent accepted it.
7. Report the Herdr session/agent name, visible status, and prompt-submission result.

## Handoff Packet

Write handoff context once under:

```text
.ai/agentops/handover/<short-task-name>/handoff.md
```

Use this packet shape:

```text
# Handoff

Goal:
<current user objective>

Current directory:
<absolute path>

Agent command:
<agent executable and autonomous launch flags>

Project/session rules:
<critical rules for tools, privacy, edits, tests, commits, deployment, or task tracking>

Current state:
<inspected, changed, created, or decided>

Files touched:
<paths with short notes>

Commands run:
<important commands and outcomes>

Known issues:
<errors, blockers, uncertainty, or "none known">

Next steps:
<ordered concrete actions>

Do not assume access to the prior conversation. Verify local state before editing.
```

Then send only:

```text
Read <handoff-packet-path> and continue the work. Do not assume access to prior conversation.
```

## Mechanics

Name handover sessions with:

```text
handover-<short-task-name>
```

The handoff packet is the source of truth. Do not paste the full handoff into Herdr and also store it in Markdown.

Do not count the handover as complete when text merely appears in the target terminal. Resolve the pane id, send `Enter`, refresh Herdr status/recent output, and confirm the new agent is working or responding.
