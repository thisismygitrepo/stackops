---
name: workflows
description: Transfer active work to a new interactive agent instance in the same tmux session. Use when the user invokes handover, asks to hand off the current task, asks to continue in a fresh agent window, or wants Codex/OpenCode/another CLI agent to pass complete working context to another instance of itself.
---

# Workflows

This skill provides one command: `handover`.

## Command: handover

Use `handover` when the user asks to transfer the current work to a new interactive agent instance. The new instance is a normal interactive agent, not a subagent. It must be started in a new window in the same tmux session, with a clear window name, and receive enough pasted context to continue without relying on the prior conversation.

### Required Behavior

1. Confirm the current shell is inside tmux by checking `TMUX`.
2. Identify the current agent command from the process tree when possible. Prefer the same CLI family:
   - `codex` hands over to `codex`
   - `opencode` hands over to `opencode`
   - another interactive agent hands over to the same executable when discoverable
3. Gather fresh local context before writing the handover note:
   - current working directory
   - active git branch and status
   - relevant task tracker state, if the repo has one
   - files changed during this session
   - commands already run and their outcomes
   - unresolved errors, blockers, and next concrete steps
4. Write a concise handover note that is directly actionable for the next agent.
5. Start a new tmux window in the current session with a descriptive name.
6. Start the selected agent CLI in that window.
7. Paste the handover note into the new agent and submit it.
8. Tell the user the new tmux window name and whether the paste succeeded.

### Handover Note Format

The pasted note must include:

```text
You are taking over this work from another interactive agent instance.

Goal:
<the user's current objective>

Current directory:
<absolute path>

Agent to continue as:
<agent command>

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

### Tmux Mechanics

After preparing the note, run the tmux commands directly. Use the current working directory for the new window.

```bash
tmux new-window -c "$PWD" -n '<short descriptive name>' '<agent command>'
tmux load-buffer '<path to handover note>'
tmux paste-buffer -d
tmux send-keys Enter
```

Prefer storing the handover note in a temporary location that is already ignored by the current project. If the current project has `.ai/tmp_scripts`, use a task-specific subdirectory there. Otherwise use a private temporary file and delete it after a successful handover.

If the target agent needs startup time before paste, wait briefly before `tmux load-buffer` and `tmux paste-buffer`. If the selected agent command requires flags or a specific entrypoint, include them in `<agent command>`.

### Window Naming

Use a name that identifies the work without being noisy:

```text
handover-<short-task-name>
```

Examples: `handover-auth-fix`, `handover-vercel-deploy`, `handover-pyright`.

### Failure Handling

If tmux is unavailable, `TMUX` is unset, the agent command cannot be identified, or the paste fails, explain the exact failure and provide the handover note in the current chat so the user can transfer it manually. Do not pretend the handover happened unless the tmux commands completed successfully.
