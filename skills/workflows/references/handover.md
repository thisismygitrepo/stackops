# Handover

Use `handover` when the user asks to transfer current work to a new interactive agent instance.

Read [herdr.md](herdr.md) before using this command.

The handover must start a normal interactive agent through `herdr`, not an internal subagent. The new agent gets a clear session name and enough submitted context to continue without the prior conversation. Use a new Herdr tab with a single pane when `herdr tab` and `herdr agent start` are available; otherwise use one new named `herdr` session. Do not hand over by splitting another agent's existing tab/window unless the user explicitly requests a pane-based handover.

## Required Behavior

1. Inspect available `herdr` commands with `herdr --help` and, when needed, `herdr session --help`; also inspect tab/window/pane help before using any layout command.
2. Identify the current agent command from the process tree.
   - `codex` hands over to `codex`
   - `opencode` hands over to `opencode`
   - another interactive agent hands over to the same executable
3. Gather fresh local context:
   - current working directory
   - active git branch and status
   - task tracker state, if any
   - files changed
   - commands run and outcomes
   - unresolved errors, blockers, and next steps
4. Write a concise handover note that is actionable for the next agent.
5. Launch the selected agent CLI through a new named `herdr` session and, when supported, its own Herdr tab with exactly one pane. When using `herdr agent start`, target a fresh tab with `--tab <tab_id>` or a workspace with `--workspace <workspace_id>` and do not pass `--split` unless the user requested panes.
6. Submit the handover note to the new agent with the shared Herdr prompt submission protocol: send the text, send an explicit `Enter` key to the target pane, and verify the agent accepted it before stopping or reporting the handover as done.
7. Tell the user the new `herdr` session name, visible status, and whether the note was confirmed submitted.

## Handover Note Format

```text
You are taking over this work from another interactive agent instance.

Goal:
<the user's current objective>

Current directory:
<absolute path>

Agent command:
<agent executable and important flags>

Project/session rules:
<critical instructions that affect command execution, privacy, tests, commits, deployment, or task tracking>

Current state:
<what has been inspected, changed, created, or decided>

Files touched:
<absolute or repo-relative paths, with short notes>

Commands run:
<important commands and outcomes>

Known issues:
<errors, blockers, uncertainty, or "none known">

Next steps:
<ordered, concrete actions>

Do not assume access to the prior conversation. Verify local state before editing.
```

## Mechanics

After preparing the note, run `herdr` commands directly. Use the current working directory for the new session unless the user asks for another directory.

Preserve the global `herdr` layout rule for handover: one new agent means one new Herdr tab with a single pane. If the installed `herdr` CLI uses different terms, map them carefully from `herdr --help` and avoid commands that split an existing tab/window by default. In current Herdr, `herdr agent start ... --split right|down` is the explicit pane-splitting path, so omit `--split` by default.

If the user explicitly requests a handover into a pane, keep the existing and new panes roughly equal with `herdr pane layout`, `herdr pane resize`, or the closest available pane command.

If the target agent command requires flags or a specific entrypoint, include them when launching or configuring the `herdr` session according to `herdr --help`.

Use a name that identifies the work without being noisy:

```text
handover-<short-task-name>
```

Examples: `handover-auth-fix`, `handover-vercel-deploy`, `handover-pyright`.

Prefer storing the handover note in a temporary location that is already ignored by the current project. If the current project has `.ai/tmp_scripts`, use a task-specific subdirectory there. Otherwise use a private temporary file and delete it after a successful handover.

If `herdr` supports direct handoff submission through `herdr update --handoff`, use that path only when the installed help or observed behavior shows it submits to the target agent. If the installed help indicates a different direct message mechanism, use the documented `herdr` mechanism.

Do not count the handover as complete just because the note text was sent or appears in the target terminal. `herdr agent send` and `herdr pane send-text` can leave literal text in the agent input buffer. Resolve the target pane id, send `herdr pane send-keys <pane_id> Enter`, then refresh Herdr status and recent output. If the note remains unsubmitted, send one additional `Enter` and verify again. Before stopping or wrapping up, confirm Herdr shows the agent working or recent output clearly shows the prompt was accepted.

## Failure Handling

If `herdr` is unavailable, the agent command cannot be identified, a session cannot be launched, or the handover note cannot be submitted, explain the exact failure and provide the handover note in the current chat.

Do not pretend the handover happened unless the `herdr` commands completed successfully and the session is visible in `herdr session list --json`.
