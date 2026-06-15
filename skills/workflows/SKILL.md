---
name: workflows
description: Manage external interactive agent workflows through herdr. Use when the user invokes handover, parallel-isolated-agents, asks to hand off current work, asks for parallel agents, asks to delegate messages to herdr-managed agent sessions, or wants Codex/OpenCode/another CLI agent to continue or coordinate work.
---

# Workflows

This skill provides three commands:

- `handover`: transfer active work to a new interactive agent session.
- `parallel-agents`: coordinate the user's external parallel agents.
- `parallel-isolated-agents`: create isolated worktrees and start one herdr-managed agent per worktree.

Use `herdr` as the process and session coordinator. `herdr` is the source of truth for external agent sessions and status. Check `herdr --help` and the relevant subcommand help before using a command shape that is not listed here.

## Command: handover

Use `handover` when the user asks to transfer current work to a new interactive agent instance.

The handover must start a normal interactive agent through `herdr`, not an internal subagent. The new agent gets a clear session name and enough submitted context to continue without the prior conversation.

### Required Behavior

1. Inspect available `herdr` commands with `herdr --help` and, when needed, `herdr session --help`.
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
5. Launch the selected agent CLI through a new named `herdr` session.
6. Submit the handover note to the new agent.
7. Tell the user the new `herdr` session name, visible status, and whether the note was submitted.

### Handover Note Format

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

### Herdr Mechanics

After preparing the note, run `herdr` commands directly. Use the current working directory for the new session unless the user asks for another directory.

Known command surface:

```bash
herdr --session '<short descriptive name>'
herdr update --handoff
herdr session list --json
herdr session attach '<session name>'
herdr session stop '<session name>' --json
herdr session delete '<session name>' --json
```

If the target agent command requires flags or a specific entrypoint, include them when launching or configuring the `herdr` session according to `herdr --help`. Use a name that identifies the work without being noisy:

```text
handover-<short-task-name>
```

Examples: `handover-auth-fix`, `handover-vercel-deploy`, `handover-pyright`.

Prefer storing the handover note in a temporary location that is already ignored by the current project. If the current project has `.ai/tmp_scripts`, use a task-specific subdirectory there. Otherwise use a private temporary file and delete it after a successful handover.

If `herdr` supports direct handoff submission through `herdr update --handoff`, use that path. If the installed help indicates a different direct message mechanism, use the documented `herdr` mechanism.

### Failure Handling

If `herdr` is unavailable, the agent command cannot be identified, a session cannot be launched, or the handover note cannot be submitted, explain the exact failure and provide the handover note in the current chat. Do not pretend the handover happened unless the `herdr` commands completed successfully and the session is visible in `herdr session list --json`.

## Command: parallel-agents

Use `parallel-agents` when the user invokes this workflow, asks for parallel agents, asks to spin up agents, asks to delegate work to external agents, or asks to coordinate multiple interactive CLI agents.

Coordinate the user's parallel agents: create external agent sessions, delegate the user's messages, collect results, report results to the user, and terminate agents when complete.

### Boundaries

1. All managed-agent work must happen through `herdr`.
2. Do not use internal subagents, hidden multi-agent mechanisms, or internal workflow delegation for managed-agent work.
3. Every managed agent must have exactly one recorded `herdr` session.
4. Use interactive CLI agents by default:
   - for Codex, start `codex`
   - for OpenCode, start `opencode`
5. Use a different agent type only when the user asks.
6. Use non-interactive CLI invocation only when the user explicitly asks for it or the target agent has no interactive mode.

### Parallel Agents Startup

Before creating or messaging agents:

1. Inspect `herdr --help` and `herdr session --help`.
2. Read `herdr session list --json` to understand existing sessions and visible statuses.
3. Identify the parallel-agents controller command from the process tree.
4. Create `.ai/workflows/parallel-agents/contracts/agents.json` if it does not exist.
5. Read the current `agents.json` before creating, messaging, collecting from, or terminating agents.

### Agent Contract File

Store managed-agent state in `.ai/workflows/parallel-agents/contracts/agents.json`. Keep the file strict JSON.

```json
{
  "controller": {
    "agent_command": "<controller agent command>"
  },
  "agents": [
    {
      "id": "<stable short id>",
      "role": "<delegated role or task>",
      "agent_command": "<cli command>",
      "herdr_session": "<session name>",
      "herdr_status": "<status from herdr, when available>",
      "worktree": "<absolute worktree path or null>",
      "status": "starting | idle | working | done | terminated | failed",
      "created_at": "<ISO-8601 timestamp>",
      "last_message_at": "<ISO-8601 timestamp or null>",
      "last_result_at": "<ISO-8601 timestamp or null>",
      "notes": "<short operational note>"
    }
  ]
}
```

Update this file after creating a session, sending a message, collecting a result, observing failure, or terminating an agent.

### Interactive Agents

Create one `herdr` session per agent. Use the current working directory unless the user explicitly asks for another directory.

```bash
herdr --session '<parallel-agent-name>'
herdr session list --json
```

After creating the session, wait for the CLI to initialize and verify it is visible through `herdr session list --json`. Send messages through the documented `herdr` interface. If the local `herdr --help` exposes a direct message or handoff command, use it.

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

Do not assume agents can see the controller's conversation. Communicate through `herdr` only.

### Collecting Results

Use `herdr` to inspect each agent session and collect visible status:

```bash
herdr session list --json
herdr session attach '<session name>'
```

If an agent is still working according to `herdr`, leave it running and mark it `working`. If it has completed, summarize its result for the user, update `agents.json`, and terminate it when no further work is needed.

Terminate agents through `herdr` only:

```bash
herdr session stop '<session name>' --json
herdr session delete '<session name>' --json
```

Never terminate sessions that are not recorded in `.ai/workflows/parallel-agents/contracts/agents.json` unless the user explicitly instructs and the target is visible in `herdr session list --json`.

## Command: parallel-isolated-agents

Use `parallel-isolated-agents` when the user wants multiple external agents to work in isolation on the same repository state, usually to test different hypotheses, compare approaches, or modify different files without colliding.

`parallel-isolated-agents` creates one git worktree per agent from the current repository, current branch, and current commit. Each agent starts inside its own worktree through `herdr`, in a new `herdr` space when the installed CLI supports spaces, with one tab or session per agent.

### Required Behavior

1. Determine how many agents the user requested. If the count is missing, ask for the count before creating worktrees.
2. Inspect `herdr --help` and relevant subcommand help for space, tab, session, and message or handoff commands.
3. Capture the source repository state:
   - repository root from `git rev-parse --show-toplevel`
   - repository name from the root directory name
   - current branch from `git branch --show-current`
   - current commit from `git rev-parse HEAD`
   - current status from `git status --short`
4. If the source repository has uncommitted changes, do not silently copy them. Ask whether the user wants to commit, stash, or continue from `HEAD` only.
5. Create a parallel-isolated-agents root under:

```text
~/.config/stackops/.ai/skills/workflows/<repo-name>-<branch-name>/<unique-id>
```

6. Create one worktree per agent under the parallel-isolated-agents root. Use branch names derived from the current branch and unique id, for example:

```text
<parallel-isolated-agents-root>/agent-01
<parallel-isolated-agents-root>/agent-02
```

7. Start one agent per worktree through `herdr`. Use a shared `herdr` space for the parallel-isolated-agents run when the installed CLI supports spaces. Use one tab per agent when the installed CLI supports tabs; otherwise use one named `herdr` session per agent.
8. Send each agent a complete, standalone instruction describing its assigned hypothesis, file area, or change strategy.
9. Record every worktree and `herdr` session in `.ai/workflows/parallel-agents/contracts/agents.json`.
10. Report the parallel-isolated-agents root, agent count, worktree paths, session names, and visible `herdr` statuses to the user.

### Worktree Commands

Use strict git worktrees from the captured commit. Do not create loose copies.

```bash
git worktree add -b '<branch-name>' '<worktree-path>' '<commit>'
git worktree list
```

Branch and path names must be shell-safe and derived from the repo name, current branch, parallel-isolated-agents id, and agent index. If the current branch name is empty, use `detached` in the parallel-isolated-agents path name and create explicit parallel-isolated-agents branch names for the worktrees.

### Herdr Layout

Prefer the most specific `herdr` layout the installed CLI supports:

- one space for the whole parallel-isolated-agents run
- one tab per agent inside that space
- one named session per agent when tabs are not exposed by `herdr --help`

Use names that connect the agent to the worktree:

```text
parallel-isolated-<repo-name>-<unique-id>-agent-01
```

Always launch each agent with its working directory set to that agent's worktree. Verify each agent is visible through `herdr session list --json` or the equivalent status command exposed by the installed `herdr`.

### Parallel Isolated Agent Instruction

Each agent instruction must include:

- the user's objective
- that agent's assigned hypothesis, file area, or change strategy
- absolute worktree path
- source repo, source branch, and source commit
- project/session rules
- allowed scope of edits
- expected output format
- instruction to verify local state before editing
- instruction to avoid touching other parallel-isolated-agents worktrees

### Failure Handling

If any worktree or `herdr` session cannot be created, stop creating additional agents, report the exact failure, and keep `agents.json` consistent with only the worktrees and sessions that actually exist. Do not delete created worktrees or terminate sessions unless the user asks or the failed operation left an unusable partial resource.

### Non-Interactive Agents

Only use non-interactive mode when required. Read the target agent CLI documentation or help output to learn the correct one-line invocation. Record the command in `agents.json` and capture the result for the user.

### Failure Handling

If `herdr` is unavailable, the current agent type cannot be identified, a session cannot be created, or an agent cannot be reached, report the exact failure and do not claim the agent exists. Keep `agents.json` consistent with what actually happened.
