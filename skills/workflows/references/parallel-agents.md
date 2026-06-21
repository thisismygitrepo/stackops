# Parallel Agents

Use `parallel-agents` when the user invokes this workflow, asks for parallel agents, asks to spin up agents, asks to delegate work to external agents, or asks to coordinate multiple interactive CLI agents.

Read [herdr.md](herdr.md) before using this command.

Coordinate the user's parallel agents: create external agent sessions, delegate the user's messages, collect results, report results to the user, and terminate agents when complete.

## Contents

- [Boundaries](#boundaries)
- [Startup](#startup)
- [Agent Index File](#agent-index-file)
- [Interactive Agents](#interactive-agents)
- [Delegating Work](#delegating-work)
- [Collecting Results](#collecting-results)
- [Failure Handling](#failure-handling)

## Boundaries

1. All managed-agent work must happen through `herdr`.
2. Do not use internal subagents, hidden multi-agent mechanisms, or internal workflow delegation for managed-agent work.
3. Every managed agent must have exactly one recorded Herdr target. Prefer a unique `herdr agent start <name>` target plus its workspace/tab/pane identifiers; use a named `herdr` session only as the fallback when agent/tab commands are unavailable.
4. Every managed agent should have its own Herdr tab by default, with one pane in that tab. Multiple agents in panes of one tab/window are allowed only when the user explicitly requests that layout; then panes must be split into roughly equal screen areas.
5. Use interactive CLI agents by default:
   - for Codex, start `codex --dangerously-bypass-approvals-and-sandbox --cd '<cwd>'`
   - for OpenCode, start `opencode run --interactive --dangerously-skip-permissions --dir '<cwd>'`
6. Use a different agent type only when the user asks.
7. Use non-interactive CLI invocation only when the user explicitly asks for it or the target agent has no interactive mode.

## Startup

Before creating or messaging agents:

1. Inspect `herdr --help` and `herdr session --help`; if layout commands exist, inspect the relevant tab/window/pane help before creating agents.
2. Read `herdr session list --json` to understand existing sessions and visible statuses.
3. Identify the parallel-agents controller command from the process tree.
4. Create `.ai/workflows/parallel-agents/contracts/agents.json` only when this workflow needs a durable recovery index across multiple operations.
5. If the index exists, read it before creating, messaging, collecting from, or terminating agents so ownership is clear.

## Agent Index File

Store only durable ownership state in `.ai/workflows/parallel-agents/contracts/agents.json`. Keep the file strict JSON. Herdr remains the live registry and activity ledger.

```json
{
  "controller": {
    "agent_command": "<controller agent command>",
    "run_id": "<stable run id>",
    "herdr_workspace": "<workspace id or null>"
  },
  "agents": [
    {
      "id": "<stable short id>",
      "role": "<delegated role or task>",
      "agent_command": "<cli command>",
      "herdr_target": "<unique Herdr agent target name, terminal id, or null>",
      "herdr_session": "<owning session name or null>",
      "herdr_workspace": "<workspace id or null>",
      "herdr_tab": "<tab id or null>",
      "herdr_pane": "<pane id or null>",
      "worktree": "<absolute worktree path or null>",
      "branch": "<worktree branch name or null>",
      "created_at": "<ISO-8601 timestamp>"
    }
  ],
  "exceptions": [
    {
      "at": "<ISO-8601 timestamp>",
      "agent_id": "<stable short id or null>",
      "event": "<failed-to-start | failed-to-message | failed-to-collect | failed-to-terminate | other>",
      "note": "<short operational note>"
    }
  ]
}
```

Update this file only when durable ownership changes: creating or closing a session, workspace, tab, pane, agent target, or worktree; assigning a stable delegated role; or recording an exception Herdr cannot represent.

Do not store `herdr_status`, full prompts, full outputs, commands run, or routine timestamps here. Use `herdr agent list`, `herdr agent get`, `herdr pane list`, `herdr agent read`, `herdr pane read`, `herdr agent explain --json`, and Herdr report commands whenever current status or activity details are needed.

## Interactive Agents

Create one `herdr` session or uniquely named Herdr agent target per agent. Use one separate Herdr tab per agent by default, each with a single pane, and use the current working directory unless the user explicitly asks for another directory.

If `herdr` has no workspace/tab command surface, fall back to one named session per agent. Do not create multiple agents as panes inside one tab/window unless the user explicitly requested that; when requested, make the pane splits roughly equal and verify the pane count.

```bash
herdr --session '<parallel-agent-name>'
herdr workspace create --cwd '<cwd>' --label '<run-name>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label '<parallel-agent-name>' --no-focus
herdr agent start '<parallel-agent-name>' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <autonomous agent argv...>
herdr session list --json
herdr agent list
herdr agent get '<parallel-agent-name>'
herdr pane list --workspace '<workspace_id>'
herdr pane report-metadata '<pane_id>' --source 'workflows:<run-id>:<agent-id>' --agent '<parallel-agent-name>' --title '<role>' --custom-status 'delegated'
```

After creating the session or agent target, wait for the CLI to initialize and verify it is visible through `herdr session list --json`, `herdr agent list`, `herdr agent get`, or the closest status command exposed by the installed `herdr`.

If `herdr` reports tab/window or pane metadata, verify the default case has one agent per Herdr tab and exactly one pane in that tab. Report a short role/title through `herdr pane report-metadata` when useful.

Send messages through the documented `herdr` interface; current Herdr exposes `herdr agent send <target> <text>` and `herdr pane send-text <pane_id> <text>`. Prefer `herdr agent send` when a unique agent target exists, but treat send commands as text insertion unless installed help explicitly says otherwise. For interactive agent instructions, follow the shared prompt submission protocol: send the text, send `herdr pane send-keys <pane_id> Enter`, and verify the agent accepted the prompt before stopping or reporting it as delegated.

Use `.ai/tmp_scripts` or another ignored project-local temporary directory for message files. Do not place temporary prompts outside the current project unless there is no ignored project-local option.

## Delegating Work

Send each agent a complete, standalone instruction. Include:

- the user's objective or delegated slice of work
- current working directory
- relevant project/session rules
- the autonomous launch/permission mode already used for the worker
- exact files, commands, or context needed
- expected output format
- whether the agent may edit files or should only inspect and report
- reminder to verify local state before acting

Do not assume agents can see the controller's conversation. Communicate through `herdr` only.

## Collecting Results

Use `herdr` to inspect each agent session and collect visible status:

```bash
herdr session list --json
herdr agent list
herdr agent get '<agent target>'
herdr agent explain '<agent target>' --json
herdr agent read '<agent target>' --source recent --lines 200
herdr pane read '<pane_id>' --source recent --lines 200
herdr wait agent-status '<pane_id>' --status done --timeout <ms>
herdr session attach '<session name>'
```

If an agent is still working according to `herdr`, leave it running and report the Herdr status. If it has completed, summarize its recent Herdr output for the user and terminate it when no further work is needed. Record only lifecycle exceptions in the local index.

Terminate agents through `herdr` only. Close the smallest Herdr target that belongs to the managed agent:

```bash
herdr tab close '<tab_id>'
herdr pane close '<pane_id>'
herdr session stop '<session name>' --json
herdr session delete '<session name>' --json
```

For the default one-agent-per-tab layout, close the indexed tab when the work is complete and no further interaction is needed. For a user-requested pane layout, close only the indexed pane.

Use `herdr session stop` or `herdr session delete` only for the named-session fallback or when the whole indexed session belongs to that one managed agent.

Never terminate sessions, tabs, or panes that are not owned by this workflow index unless the user explicitly instructs and the target is visible through Herdr status commands.

## Failure Handling

If `herdr` is unavailable, the current agent type cannot be identified, a session cannot be created, or an agent cannot be reached, report the exact failure and do not claim the agent exists.

Keep the local index consistent with what actually happened.
