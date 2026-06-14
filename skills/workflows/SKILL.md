---
name: workflows
description: Manage external interactive agent workflows in the current tmux session. Use when the user invokes handover, asks to hand off current work, asks for an agents manager, asks to delegate messages to tmux-based agent windows, or wants Codex/OpenCode/another CLI agent to continue or coordinate work.
---

# Workflows

This skill provides two commands:

- `handover`: transfer active work to a new interactive agent window.
- `manager`: act as the user's external agents manager.

## Command: handover

Use `handover` when the user asks to transfer the current work to a new interactive agent instance. This is a normal interactive agent, not an internal subagent. It must be started in a new window in the same tmux session, with a clear window name, and receive enough pasted context to continue without relying on the prior conversation.

### Required Behavior

1. Confirm the current shell is inside tmux by checking `TMUX`.
2. Identify the current agent command from the process tree. Prefer the same CLI family:
   - `codex` hands over to `codex`
   - `opencode` hands over to `opencode`
   - another interactive agent hands over to the same executable
3. Gather fresh local context:
   - current working directory
   - active git branch and status
   - task tracker state, if present
   - files changed
   - commands already run and outcomes
   - unresolved errors, blockers, and next concrete steps
4. Write a concise handover note actionable for the next agent.
5. Start a new tmux window with a descriptive name.
6. Start the selected agent CLI in that window.
7. Paste the handover note into the new agent and submit it.
8. Tell the user the new tmux window name and whether the paste succeeded.

### Handover Note Format

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
<what inspected, changed, created, or decided>

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

Use a name that identifies the work without being noisy:

```text
handover-<short-task-name>
```

Examples: `handover-auth-fix`, `handover-vercel-deploy`, `handover-pyright`.

### Failure Handling

If tmux is unavailable, `TMUX` is unset, the agent command cannot be identified, or the paste fails, explain the exact failure and provide the handover note in the current chat so the user can transfer it manually. Do not pretend the handover happened unless the tmux commands completed successfully.

## Command: manager

Use `manager` when the user invokes this workflow, asks for an agents manager, asks to spin up agents, asks to delegate work to external agents, or asks to coordinate multiple interactive CLI agents.

When this command is active, act as the user's agents manager. Your job is to create external agent processes, delegate the user's messages to them, collect their results, report those results to the user, and terminate agents when their work is complete or no longer needed.

### Core Rules

1. All manager work must happen inside the current tmux session.
2. Do not touch tmux sessions outside the current one.
3. Every managed agent must live in exactly one tmux window.
4. Do not use internal subagents, hidden multi-agent mechanisms, or internal workflow delegation for managed-agent work. These agents are external CLI processes visible to the user in tmux.
5. By default, create agents of the same type as the manager:
   - if the manager is Codex, start `codex`
   - if the manager is OpenCode, start `opencode`
   - otherwise identify the current executable from the process tree and start the same CLI
6. Use a different agent type only when the user explicitly asks for it.
7. Agents are interactive by default. Use non-interactive CLI invocation only when the user explicitly asks for non-interactive agents.
8. Maintain a record of managed agents at `.ai/workflows/manager/contracts/agents.json`.

### Startup Checklist

1. Confirm `TMUX` is set.
2. Identify the current tmux session with `tmux display-message -p '#S'`.
3. Identify the current window with `tmux display-message -p '#I:#W'`.
4. Identify the manager's agent command from the process tree.
5. Create `.ai/workflows/manager/contracts/agents.json` if it does not exist.
6. Read the current `agents.json` before creating, messaging, collecting from, or terminating agents.

### Agent Contract File

Store managed-agent state in `.ai/workflows/manager/contracts/agents.json`. Keep the file strict JSON.

Use this structure:

```json
{
  "manager": {
    "tmux_session": "<current session name>",
    "window": "<current manager window index:name>",
    "agent_command": "<manager agent command>"
  },
  "agents": [
    {
      "id": "<stable short id>",
      "role": "<delegated role or task>",
      "agent_command": "<cli command>",
      "tmux_session": "<current session name>",
      "window": "<window index:name>",
      "status": "starting | idle | working | done | terminated | failed",
      "created_at": "<ISO-8601 timestamp>",
      "last_message_at": "<ISO-8601 timestamp or null>",
      "last_result_at": "<ISO-8601 timestamp or null>",
      "notes": "<short operational note>"
    }
  ]
}
```

Update this file immediately after creating a window, sending a message, collecting a result, observing failure, or terminating an agent.

### Creating Interactive Agents

Create one tmux window per agent in the current tmux session. Use the current working directory unless the user explicitly asks for another directory.

```bash
tmux new-window -c "$PWD" -n '<manager-agent-name>' '<agent command>'
```

After creating the window, wait a few seconds for the CLI to initialize. Then send messages through tmux as a normal user would:

```bash
tmux load-buffer '<path to message file>'
tmux paste-buffer -t '<window target>' -d
tmux send-keys -t '<window target>' Enter
```

Use `.ai/tmp_scripts` or another ignored project-local temporary directory for message files. Do not place temporary prompts outside the current project unless there is no ignored project-local option.

### Delegating Work

Send each agent a complete, standalone instruction. Include:

- the user's objective or delegated slice of work
- current working directory
- relevant project/session rules
- exact files, commands, or context needed
- expected output format
- whether the agent may edit files or should only inspect and report
- reminder to verify local state before acting

Do not assume agents can see the manager's conversation. Communicate through tmux only.

### Collecting Results

Use tmux to inspect each agent window and collect results:

```bash
tmux capture-pane -t '<window target>' -p -S -200
```

If an agent is still working, leave it running and mark it `working`. If it has completed, summarize its result for the user, update `agents.json`, and terminate it when no further work is needed.

### Terminating Agents

Terminate agents inside the current tmux session only. Prefer graceful termination first:

```bash
tmux send-keys -t '<window target>' C-c
tmux send-keys -t '<window target>' C-d
```

If the process remains and the work is complete or failed beyond recovery, close only that agent's tmux window:

```bash
tmux kill-window -t '<window target>'
```

Never kill the manager window. Never kill windows that are not recorded in `.ai/workflows/manager/contracts/agents.json` unless the user explicitly instructs it and the target is in the current tmux session.

### Non-Interactive Agents

Only use non-interactive mode when the user explicitly asks for it. Before doing so, read the target agent CLI documentation or help output to learn the correct one-line invocation. Then record the command in `agents.json` and capture the result for the user.

### Failure Handling

If tmux is unavailable, `TMUX` is unset, the current agent type cannot be identified, a window cannot be created, or an agent cannot be reached, report the exact failure and do not claim the agent exists. Keep `agents.json` consistent with what actually happened.
