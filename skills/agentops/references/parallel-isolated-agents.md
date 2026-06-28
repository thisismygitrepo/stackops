# Parallel Isolated Agents

Use `parallel-isolated-agents` when the user wants multiple external agents working from the same repo state without colliding. Read [herdr.md](herdr.md) first.

Create one `wt`/Worktrunk git worktree per agent from the current repository state. Start each agent in its own worktree through Herdr.

## Rules

1. Use `wt` for worktree lifecycle, path selection, hooks, JSON output, cleanup, and merge support.
2. Keep the source worktree clean. Startup may only create temporary local worktree/branch metadata.
3. Do not commit, stash, merge, push, tag, create PRs, run `wt merge`, run `wt step commit`, run `wt step squash`, run `wt step push`, or change the main/default branch unless the user explicitly asks after review.
4. If source has uncommitted changes, ask whether to start from `HEAD` only or whether the user wants to commit/stash first. Never commit or stash without explicit instruction.
5. If the user requires zero git metadata changes, explain that real git worktrees require local metadata before proceeding.

## Startup

1. Determine the requested agent count; ask if missing.
2. Inspect `herdr --help`, relevant Herdr subcommand help, `wt --help`, `wt switch --help`, and `wt list --format json`.
3. Capture source state:
   - repo root: `git rev-parse --show-toplevel`
   - repo name: root directory name
   - branch: `git branch --show-current`
   - commit: `git rev-parse HEAD`
   - status: `git status --short`
4. Create a run id and branch names:

```text
parallel-isolated/<repo-name>-<branch-name>-<run-id>-agent-01
parallel-isolated/<repo-name>-<branch-name>-<run-id>-agent-02
```

5. Create one worktree per agent and record the JSON `path`:

```bash
wt -C '<repo-root>' switch --create '<agent-branch>' --base=@ --format json --no-cd
wt -C '<repo-root>' list --format json
```

6. Create one Herdr workspace for the run, one tab per agent, and one agent target per worktree:

```bash
herdr workspace create --cwd '<repo-root>' --label '<run-name>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<worktree>' --label '<agent-name>' --no-focus
herdr agent start '<agent-name>' --cwd '<worktree>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <autonomous agent argv...>
```

7. Write each agent's task packet and send only the packet path using the Herdr prompt protocol from [herdr.md](herdr.md).
8. Index every worktree, Herdr identifier, and packet path in `.ai/agentops/parallel-isolated-agents/contracts/agents.json`.
9. Report run id, agent count, branch names, worktree paths, Herdr targets/IDs, and visible statuses.

## Worktrees

Use strict git worktrees through `wt`; do not create loose copies. Use `--no-cd` so the controller passes explicit worktree paths to Herdr.

Branch names must be shell-safe and derived from repo name, source branch, run id, and agent index.

If the source branch is empty, use `detached` in the branch name and create explicit branches from the captured commit before opening them through `wt`:

```bash
git -C '<repo-root>' branch '<agent-branch>' '<commit>'
wt -C '<repo-root>' switch '<agent-branch>' --format json --no-cd
```

Use the same explicit-branch sequence when exact captured-commit isolation matters and the source branch may move before worktree creation.

Use `wt remove '<agent-branch>'` for cleanup. Use `wt merge` only after the user explicitly asks to integrate a reviewed agent branch.

## Layout

Default Herdr layout: one workspace, one tab per agent, one pane per tab. Use panes only when the user explicitly asks; then create one tab/window, split panes evenly, launch one agent per pane, and verify pane count equals agent count.

Name agents after the worktree:

```text
parallel-isolated-<repo-name>-<run-id>-agent-01
```

Always set each agent cwd to its own worktree. Verify visibility with `herdr agent list`, `herdr agent get`, and `herdr pane list`.

## Communication Records

For non-trivial delegation, create per-agent packets under:

```text
.ai/agentops/parallel-isolated-agents/runs/<run-id>/
  run.md
  state.md
  index.md
  agents/<agent-id>/task.md
  agents/<agent-id>/result.md
```

Use `run.md` for shared source repo, source branch, source commit, objective, project rules, and controller metadata. Use `state.md` only for bounded coordination state that every isolated agent may need. Use `index.md` for compact pointers to task/result packets, Herdr targets, branches, and worktrees.

Each isolated agent owns its `agents/<agent-id>/` record directory and its own git worktree. It must not write records in another agent's directory.

The isolated-agent JSON contract stores the same ownership shape as `parallel-agents`, plus branch/worktree identifiers and the `task_path` and `result_path` packet pointers.

## Agent Instruction

Write each agent instruction to `agents/<agent-id>/task.md`. Include:

- user objective
- assigned hypothesis, file area, or strategy
- absolute worktree path
- source repo, branch, and commit
- project/session rules
- autonomous launch/permission mode already used
- allowed edit scope
- expected output format
- instruction to verify local state before editing
- instruction not to touch other isolated worktrees
- instruction not to change git history/refs unless the controller relays an explicit user request
- result packet path to write before reporting complete

Then send only:

```text
Read <task-packet-path> and follow it. Do not assume access to prior conversation.
```

## Non-Interactive Agents

Use non-interactive mode only when required. Inspect the target CLI help for the one-shot invocation and run it through a Herdr-managed pane with `herdr pane run` so output remains visible.
