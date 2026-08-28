# Handover

Use `handover` when the user asks to transfer current work to a new interactive agent instance. Read [herdr.md](herdr.md) first.

Start a normal external agent through `herdr`, not an internal subagent. Use a fresh Herdr tab with one pane. Split into panes only when the user explicitly asks for pane-based handover.

## Protocol

1. Complete the Herdr preflight and inspect `herdr --help` plus relevant workspace/tab/pane/agent help.
2. Identify the current interactive agent executable from the process tree:
   - `codex` hands over to `codex`
   - `opencode` hands over to `opencode`
   - `pi` hands over to `pi`
   - another CLI hands over to the same executable
3. Gather fresh context: cwd, branch, git status, changed files, task tracker state, commands run, outcomes, blockers, and next steps.
4. Write the handoff packet using the format below.
5. Create a `handover-<short-task-name>` workspace in the default session and use its returned root tab/pane. Launch the same agent kind there with `herdr agent start` and the native autonomous arguments from [herdr.md](herdr.md), in the current cwd unless the user asks otherwise.
6. Submit a short packet-pointer prompt with `herdr agent prompt ... --wait`. Do not send a second Enter. If it returns `blocked`, inspect the agent and ask the user before responding to the dialog.
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

Name handover workspaces and agents with:

```text
handover-<short-task-name>
```

Keep the live agent name within Herdr's 32-character limit and allowed character set.

The handoff packet is the source of truth. Do not paste the full handoff into Herdr and also store it in Markdown.

Do not count the handover as complete until `agent prompt` confirms a lifecycle change or settled state and fresh `agent get`/`agent read` output agrees.
