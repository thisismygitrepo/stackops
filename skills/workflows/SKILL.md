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

For every workflow and every `herdr` command, keep the distinction between tabs/windows and panes explicit. Herdr exposes top-level terminal targets as `tab` resources inside a `workspace`; treat a user request for tabs or windows as one Herdr tab per agent unless the installed CLI exposes a separate window concept. A pane is only a split inside one tab/window. The default layout is one agent per separate Herdr tab, or one named `herdr` session per agent when workspace/tab commands are not available. Do not put multiple agents into panes inside one tab/window unless the user explicitly asks for that pane-based layout. If the user does ask for multiple agents as panes in one tab/window, split the screen roughly equally across panes, verify the pane count matches the requested agents through `herdr pane list` or equivalent metadata, and keep each pane tied to exactly one agent.

## Command: handover

Use `handover` when the user asks to transfer current work to a new interactive agent instance.

The handover must start a normal interactive agent through `herdr`, not an internal subagent. The new agent gets a clear session name and enough submitted context to continue without the prior conversation. Use a new Herdr tab with a single pane when `herdr tab` and `herdr agent start` are available; otherwise use one new named `herdr` session. Do not hand over by splitting another agent's existing tab/window unless the user explicitly requests a pane-based handover.

### Required Behavior

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

Preserve the global `herdr` layout rule for handover: one new agent means one new Herdr tab with a single pane. If the installed `herdr` CLI uses different terms, map them carefully from `herdr --help` and avoid commands that split an existing tab/window by default. In current Herdr, `herdr agent start ... --split right|down` is the explicit pane-splitting path, so omit `--split` by default. If the user explicitly requests a handover into a pane, keep the existing and new panes roughly equal with `herdr pane layout`, `herdr pane resize`, or the closest available pane command.

Known command surface:

```bash
herdr --session '<short descriptive name>'
herdr workspace create --cwd '<cwd>' --label '<short descriptive name>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label '<short descriptive name>' --no-focus
herdr agent start '<short descriptive name>' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <agent argv...>
herdr update --handoff
herdr session list --json
herdr agent list
herdr tab list --workspace '<workspace_id>'
herdr pane list --workspace '<workspace_id>'
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
3. Every managed agent must have exactly one recorded Herdr target. Prefer a unique `herdr agent start <name>` target plus its workspace/tab/pane identifiers; use a named `herdr` session only as the fallback when agent/tab commands are unavailable.
4. Every managed agent should have its own Herdr tab by default, with one pane in that tab. Multiple agents in panes of one tab/window are allowed only when the user explicitly requests that layout; then panes must be split into roughly equal screen areas.
5. Use interactive CLI agents by default:
   - for Codex, start `codex`
   - for OpenCode, start `opencode`
6. Use a different agent type only when the user asks.
7. Use non-interactive CLI invocation only when the user explicitly asks for it or the target agent has no interactive mode.

### Parallel Agents Startup

Before creating or messaging agents:

1. Inspect `herdr --help` and `herdr session --help`; if layout commands exist, inspect the relevant tab/window/pane help before creating agents.
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
      "herdr_session": "<owning session name or null>",
      "herdr_agent": "<unique Herdr agent target name or null>",
      "herdr_workspace": "<workspace id or null>",
      "herdr_tab": "<tab id or null>",
      "herdr_pane": "<pane id or null>",
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

Update this file after creating a session, agent target, workspace, tab, or pane; sending a message; collecting a result; observing failure; or terminating an agent.

### Interactive Agents

Create one `herdr` session or uniquely named Herdr agent target per agent. Use one separate Herdr tab per agent by default, each with a single pane, and use the current working directory unless the user explicitly asks for another directory. If `herdr` has no workspace/tab command surface, fall back to one named session per agent. Do not create multiple agents as panes inside one tab/window unless the user explicitly requested that; when requested, make the pane splits roughly equal and verify the pane count.

```bash
herdr --session '<parallel-agent-name>'
herdr workspace create --cwd '<cwd>' --label '<run-name>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label '<parallel-agent-name>' --no-focus
herdr agent start '<parallel-agent-name>' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <agent argv...>
herdr session list --json
herdr agent list
herdr pane list --workspace '<workspace_id>'
```

After creating the session or agent target, wait for the CLI to initialize and verify it is visible through `herdr session list --json`, `herdr agent list`, or the closest status command exposed by the installed `herdr`. If `herdr` reports tab/window or pane metadata, verify the default case has one agent per Herdr tab and exactly one pane in that tab. Send messages through the documented `herdr` interface; current Herdr exposes `herdr agent send <target> <text>` and `herdr pane send-text <pane_id> <text>`. Prefer `herdr agent send` when a unique agent target exists.

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
herdr agent list
herdr agent read '<agent target>' --source recent --lines 200
herdr pane read '<pane_id>' --source recent --lines 200
herdr session attach '<session name>'
```

If an agent is still working according to `herdr`, leave it running and mark it `working`. If it has completed, summarize its result for the user, update `agents.json`, and terminate it when no further work is needed.

Terminate agents through `herdr` only. Close the smallest Herdr target that belongs to the managed agent:

```bash
herdr tab close '<tab_id>'
herdr pane close '<pane_id>'
herdr session stop '<session name>' --json
herdr session delete '<session name>' --json
```

For the default one-agent-per-tab layout, close the recorded tab when the work is complete and no further interaction is needed. For a user-requested pane layout, close only the recorded pane. Use `herdr session stop` or `herdr session delete` only for the named-session fallback or when the whole recorded session belongs to that one managed agent. Never terminate sessions, tabs, or panes that are not recorded in `.ai/workflows/parallel-agents/contracts/agents.json` unless the user explicitly instructs and the target is visible through Herdr status commands.

## Command: parallel-isolated-agents

Use `parallel-isolated-agents` when the user wants multiple external agents to work in isolation on the same repository state, usually to test different hypotheses, compare approaches, or modify different files without colliding.

`parallel-isolated-agents` creates one git worktree per agent from the current repository, current branch, and current commit. Each agent starts inside its own worktree through `herdr`. Use a separate `herdr` workspace for the run when the installed CLI supports workspaces, then one Herdr tab per agent inside that workspace. Never place multiple agents as panes inside the same tab/window unless the user explicitly asks for that layout; if they do, split the panes roughly equally.

### Required Behavior

1. Determine how many agents the user requested. If the count is missing, ask for the count before creating worktrees.
2. Inspect `herdr --help` and relevant subcommand help for workspace, tab/window, pane, session, message, or handoff commands.
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

7. Start one agent per worktree through `herdr`. If `herdr workspace create`, `herdr tab create`, and `herdr agent start` exist, create one workspace for the parallel-isolated-agents run, create one tab per agent with `herdr tab create --workspace <workspace_id> --cwd <worktree> --label <agent-name> --no-focus`, then launch the agent with `herdr agent start <agent-name> --cwd <worktree> --workspace <workspace_id> --tab <tab_id> --no-focus -- <agent argv...>`. If workspaces are unavailable but tabs exist, create one tab per agent and verify each tab has exactly one pane. Otherwise use one named `herdr` session per agent. Use panes only when the user explicitly asked for a pane-based layout; in that case, create one tab/window, split it into roughly equal panes, and launch exactly one agent per pane.
8. Send each agent a complete, standalone instruction describing its assigned hypothesis, file area, or change strategy.
9. Record every worktree and Herdr session/agent/workspace/tab/pane identifier in `.ai/workflows/parallel-agents/contracts/agents.json`.
10. Report the parallel-isolated-agents root, agent count, worktree paths, Herdr target names and IDs, and visible `herdr` statuses to the user.

### Worktree Commands

Use strict git worktrees from the captured commit. Do not create loose copies.

```bash
git worktree add -b '<branch-name>' '<worktree-path>' '<commit>'
git worktree list
```

Branch and path names must be shell-safe and derived from the repo name, current branch, parallel-isolated-agents id, and agent index. If the current branch name is empty, use `detached` in the parallel-isolated-agents path name and create explicit parallel-isolated-agents branch names for the worktrees.

### Herdr Layout

Prefer the least crowded `herdr` layout the installed CLI supports:

- one workspace for the whole parallel-isolated-agents run, created with `herdr workspace create --cwd <repo-root> --label <run-name> --no-focus`
- one Herdr tab per agent inside that workspace, created with `herdr tab create --workspace <workspace_id> --cwd <worktree> --label <agent-name> --no-focus`, followed by `herdr agent start <agent-name> --cwd <worktree> --workspace <workspace_id> --tab <tab_id> --no-focus -- <agent argv...>`
- one named session per agent only when workspace or tab/window commands are not exposed by `herdr --help`
- one shared tab/window with multiple panes only when the user explicitly asks for panes; use `herdr agent start ... --split right|down -- <agent argv...>` or `herdr pane split ... --ratio FLOAT` according to installed help, split panes into roughly equal sizes, and run exactly one agent per pane

Do not create more than one agent pane in a tab/window by default. Before launching agents, check `herdr tab list --workspace <workspace_id>` and `herdr pane list --workspace <workspace_id>` when available; after each launch, verify the target tab has exactly one pane unless the user requested panes. If a command would add a pane to an existing tab/window and the user did not request panes, stop and choose workspace/tab creation instead. In current Herdr, this primarily means avoiding `herdr agent start --split` and `herdr pane split` by default. If the user did request panes, verify the final pane count equals the agent count and rebalance the pane layout with `herdr pane resize` when needed.

Use names that connect the agent to the worktree:

```text
parallel-isolated-<repo-name>-<unique-id>-agent-01
```

Always launch each agent with its working directory set to that agent's worktree. Verify each agent is visible through `herdr agent list`, `herdr session list --json`, or the equivalent status command exposed by the installed `herdr`.

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
