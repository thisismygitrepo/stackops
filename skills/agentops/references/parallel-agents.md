# Parallel Agents

Use `parallel-agents` when the user asks for parallel external agents, delegation to Herdr-managed agents, or coordination of multiple interactive CLI agents. Read [herdr.md](herdr.md) first.

Coordinate agent creation, delegation, result collection, reporting, and shutdown through `herdr`.

## Boundaries

1. Managed-agent work must happen through `herdr`.
2. Do not use internal subagents or hidden delegation.
3. Use one recorded Herdr target per managed agent.
4. Default to one Herdr tab per agent, one pane per tab. Use multi-pane layouts only when the user asks.
5. Use interactive agents by default with the autonomous argv from [herdr.md](herdr.md).
6. Use a different agent type or non-interactive mode only when requested or when the target has no interactive mode.

## Startup

Before creating or messaging agents:

1. Inspect `herdr --help` and relevant workspace/tab/pane/agent help.
2. Read existing Herdr sessions/agents so ownership is clear.
3. Identify the controller command from the process tree.
4. Create `.ai/agentops/parallel-agents/contracts/agents.json` only when durable recovery across multiple operations is needed.
5. If the index exists, read it before creating, messaging, collecting from, or terminating agents.

## Agent Index

Store only durable ownership state in `.ai/agentops/parallel-agents/contracts/agents.json`. Herdr remains the live registry.

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
      "herdr_target": "<Herdr agent target or null>",
      "herdr_workspace": "<workspace id or null>",
      "herdr_tab": "<tab id or null>",
      "herdr_pane": "<pane id or null>",
      "worktree": "<absolute worktree path or null>",
      "branch": "<worktree branch name or null>",
      "task_path": "<agent task packet path or null>",
      "result_path": "<agent result packet path or null>",
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

Update the index only for durable ownership changes, packet paths, or exceptions Herdr cannot represent. Do not store live statuses, full prompts, full outputs, command history, or routine timestamps.

## Communication Records

For non-trivial delegation, create per-agent packets under:

```text
.ai/agentops/parallel-agents/runs/<run-id>/
  run.md
  state.md
  index.md
  agents/<agent-id>/task.md
  agents/<agent-id>/result.md
```

Use `run.md` for shared objective, scope, project rules, and controller metadata. Use `state.md` only for bounded coordination state that every agent may need. Use `index.md` for compact pointers to agent task/result packets.

Each agent owns its `agents/<agent-id>/` directory. Agents must write results there instead of relying on the controller to scrape long terminal output. Herdr still remains the source of live status and recent output.

## Create Agents

Use the current cwd unless the user asks for another directory.

```bash
herdr workspace create --cwd '<cwd>' --label '<run-name>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label '<agent-name>' --no-focus
herdr agent start '<agent-name>' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <autonomous agent argv...>
herdr agent list
herdr agent get '<agent-name>'
herdr pane list --workspace '<workspace_id>'
herdr pane report-metadata '<pane_id>' --source 'agentops:<run-id>:<agent-id>' --agent '<agent-name>' --title '<role>' --custom-status 'delegated'
```

After launch, verify the agent target exists, the tab has one pane, and the CLI is ready. Submit the task packet path using the Herdr prompt protocol from [herdr.md](herdr.md).

## Delegation Prompt

Write each agent's standalone instruction to `agents/<agent-id>/task.md`. Include:

- user objective or delegated slice
- current working directory
- project/session rules
- autonomous launch/permission mode already used
- exact files, commands, or context needed
- expected output format
- whether edits are allowed or the agent should inspect only
- requirement to verify local state before acting
- result packet path to write before reporting complete

Do not assume agents can see the controller conversation.

Then send only:

```text
Read <task-packet-path> and follow it. Do not assume access to prior conversation.
```

## Collect And Close

Inspect agents through Herdr:

```bash
herdr agent list
herdr agent get '<agent target>'
herdr agent explain '<agent target>' --json
herdr agent read '<agent target>' --source recent --lines 200
herdr pane read '<pane_id>' --source recent --lines 200
herdr wait agent-status '<pane_id>' --status done --timeout <ms>
```

If an agent is still working, report Herdr status and leave it running. If complete, read its result packet first, use Herdr recent output only to clarify visible status or missing results, and close the smallest owned Herdr target:

```bash
herdr tab close '<tab_id>'
herdr pane close '<pane_id>'
```

Never terminate targets not owned by this workflow index unless the user explicitly asks.
