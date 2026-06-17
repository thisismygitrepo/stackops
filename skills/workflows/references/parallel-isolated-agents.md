# Parallel Isolated Agents

Use `parallel-isolated-agents` when the user wants multiple external agents to work in isolation on the same repository state, usually to test different hypotheses, compare approaches, or modify different files without colliding.

Read [herdr.md](herdr.md) before using this command.

## Contents

- [Core Protocol](#core-protocol)
- [Required Behavior](#required-behavior)
- [Worktree Commands](#worktree-commands)
- [Herdr Layout](#herdr-layout)
- [Agent Instruction](#agent-instruction)
- [Non-Interactive Agents](#non-interactive-agents)
- [Failure Handling](#failure-handling)

## Core Protocol

`parallel-isolated-agents` creates one `wt`/Worktrunk-managed git worktree per agent from the current repository, current branch, and current commit. Each agent starts inside its own worktree through `herdr`.

Use `wt` as the worktree lifecycle manager when it is available: it computes configured paths, runs configured hooks, supports JSON output for path capture, and provides cleanup/merge commands.

Use a separate `herdr` workspace for the run when the installed CLI supports workspaces, then one Herdr tab per agent inside that workspace. Never place multiple agents as panes inside the same tab/window unless the user explicitly asks for that layout; if they do, split the panes roughly equally.

Keep the source repository's main worktree and git history clean. During isolated-agent startup, the only allowed git state change is the temporary local worktree/branch metadata required by `wt switch --create` or the documented fallback.

Do not commit, stash, merge, push, tag, create PRs, run `wt merge`, run `wt step commit`, run `wt step squash`, run `wt step push`, or change the main/default branch unless the user explicitly asks after reviewing the work.

If the user requires zero git metadata registration at startup, stop and explain that real git worktrees cannot be created without local git metadata; ask whether to proceed with temporary `wt` worktrees or use a non-worktree copy strategy.

## Required Behavior

1. Determine how many agents the user requested. If the count is missing, ask for the count before creating worktrees.
2. Inspect `herdr --help` and relevant subcommand help for workspace, tab/window, pane, session, message, or handoff commands. Inspect `wt --help`, `wt switch --help`, and `wt list -h` or `wt list --format json` before creating worktrees.
3. Capture the source repository state:
   - repository root from `git rev-parse --show-toplevel`
   - repository name from the root directory name
   - current branch from `git branch --show-current`
   - current commit from `git rev-parse HEAD`
   - current status from `git status --short`
4. If the source repository has uncommitted changes, do not silently copy them. Ask whether the user wants to continue from `HEAD` only, or explicitly wants the controller to commit or stash first. Do not commit or stash without that explicit request.
5. Create a stable run id and unique branch names derived from the repo name, source branch, run id, and agent index:

```text
parallel-isolated/<repo-name>-<branch-name>-<unique-id>-agent-01
parallel-isolated/<repo-name>-<branch-name>-<unique-id>-agent-02
```

6. Create one worktree per agent with `wt switch`. Do not choose the worktree path manually when `wt` is available; record the `path` field reported by `wt --format json`.

```bash
wt -C '<repo-root>' switch --create '<agent-branch>' --base=@ --format json --no-cd
```

7. Start one agent per worktree through `herdr`. If `herdr workspace create`, `herdr tab create`, and `herdr agent start` exist, create one workspace for the parallel-isolated-agents run, create one tab per agent with `herdr tab create --workspace <workspace_id> --cwd <worktree> --label <agent-name> --no-focus`, then launch the agent with `herdr agent start <agent-name> --cwd <worktree> --workspace <workspace_id> --tab <tab_id> --no-focus -- <agent argv...>`.
8. If workspaces are unavailable but tabs exist, create one tab per agent and verify each tab has exactly one pane. Otherwise use one named `herdr` session per agent. Use panes only when the user explicitly asked for a pane-based layout; in that case, create one tab/window, split it into roughly equal panes, and launch exactly one agent per pane.
9. Send each agent a complete, standalone instruction describing its assigned hypothesis, file area, or change strategy.
10. Index every worktree and Herdr session/agent/workspace/tab/pane identifier in `.ai/workflows/parallel-agents/contracts/agents.json`; leave status, recent output, command history, and routine timestamps in Herdr.
11. Report the run id, agent count, branch names, `wt` worktree paths, Herdr target names and IDs, and visible `herdr` statuses to the user.

## Worktree Commands

Use strict git worktrees through Worktrunk (`wt`) from the captured source state. Do not create loose copies.

Use `--no-cd` because controller agents should pass the returned worktree path to `herdr --cwd` instead of relying on shell integration to change directories. Record the `path` field from JSON output as the worktree path.

```bash
wt -C '<repo-root>' switch --create '<agent-branch>' --base=@ --format json --no-cd
wt -C '<repo-root>' list --format json
```

Branch names must be shell-safe and derived from the repo name, current branch, parallel-isolated-agents id, and agent index.

If the current branch name is empty, use `detached` in the branch name and create explicit branches from the captured commit before opening them through `wt`:

```bash
git -C '<repo-root>' branch '<agent-branch>' '<commit>'
wt -C '<repo-root>' switch '<agent-branch>' --format json --no-cd
```

If exact captured-commit isolation is required and the source branch may move before worktree creation, use the same `git branch <agent-branch> <commit>` plus `wt switch <agent-branch>` sequence.

If `wt` is unavailable or cannot create a required worktree, fall back to raw git worktrees under a private run root and record the exception:

```bash
git -C '<repo-root>' worktree add -b '<agent-branch>' '<worktree-path>' '<commit>'
git -C '<repo-root>' worktree list
```

Use `wt remove '<agent-branch>'` for cleanup when the user is done with an isolated agent worktree.

Use `wt merge` from an agent worktree only when the user explicitly asks to integrate that agent's branch after the work is done; otherwise collect results and leave review/merge decisions to the controller and user.

## Herdr Layout

Prefer the least crowded `herdr` layout the installed CLI supports:

- one workspace for the whole parallel-isolated-agents run, created with `herdr workspace create --cwd <repo-root> --label <run-name> --no-focus`
- one Herdr tab per agent inside that workspace, created with `herdr tab create --workspace <workspace_id> --cwd <worktree> --label <agent-name> --no-focus`, followed by `herdr agent start <agent-name> --cwd <worktree> --workspace <workspace_id> --tab <tab_id> --no-focus -- <agent argv...>`
- one named session per agent only when workspace or tab/window commands are not exposed by `herdr --help`
- one shared tab/window with multiple panes only when the user explicitly asks for panes; use `herdr agent start ... --split right|down -- <agent argv...>` or `herdr pane split ... --ratio FLOAT` according to installed help, split panes into roughly equal sizes, and run exactly one agent per pane

Do not create more than one agent pane in a tab/window by default. If a command would add a pane to an existing tab/window and the user did not request panes, stop and choose workspace/tab creation instead.

In current Herdr, this primarily means avoiding `herdr agent start --split` and `herdr pane split` by default. If the user did request panes, verify the final pane count equals the agent count and rebalance the pane layout with `herdr pane resize` when needed.

Use names that connect the agent to the worktree:

```text
parallel-isolated-<repo-name>-<unique-id>-agent-01
```

Always launch each agent with its working directory set to that agent's worktree.

Verify each agent is visible through `herdr agent list`, `herdr session list --json`, or the equivalent status command exposed by the installed `herdr`.

## Agent Instruction

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
- instruction not to commit, stash, merge, push, tag, create PRs, run `wt merge`, or otherwise change git history/refs unless the controller later relays an explicit user request

## Non-Interactive Agents

Only use non-interactive mode when required. Read the target agent CLI documentation or help output to learn the correct one-line invocation.

Prefer running the command through a managed Herdr pane with `herdr pane run` so the command and output stay in Herdr scrollback.

If Herdr cannot represent the command, record a short exception in the local index and capture the result for the user.

## Failure Handling

If any worktree or `herdr` session cannot be created, stop creating additional agents, report the exact failure, and keep the local index consistent with only the worktrees and Herdr targets that actually exist.

Add a short exception entry only when Herdr cannot represent the failure.

Do not delete created worktrees or terminate sessions unless the user asks or the failed operation left an unusable partial resource.

If `herdr` is unavailable, the current agent type cannot be identified, a session cannot be created, or an agent cannot be reached, report the exact failure and do not claim the agent exists. Keep the local index consistent with what actually happened.
