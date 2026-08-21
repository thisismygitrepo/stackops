---
name: agentops
description: Manage external interactive agent operations through herdr and wt/Worktrunk isolated worktrees. Use when the user invokes handover, iter, parallel-iters, parallel-agents, parallel-isolated-agents, asks to hand off current work, asks for goal-directed iterative improvement, asks for multiple scope-separated iter chains, asks for parallel agents, asks to delegate messages to herdr-managed agent sessions, or wants Codex/OpenCode/Pi/another CLI agent to continue or coordinate work.
---

# AgentOps

Coordinate external agents through `herdr`:

- `handover`: transfer active work.
- `iter`: run a goal-directed chain, one pass per agent.
- `parallel-iters`: run independent, scope-separated iteration chains.
- `parallel-agents`: coordinate the user's external parallel agents.
- `parallel-isolated-agents`: run agents in `wt`/Worktrunk worktrees.

## References

Before acting, read [Herdr mechanics](references/herdr.md) and the command reference:

- `handover`: [references/handover.md](references/handover.md)
- `iter`: [references/iter.md](references/iter.md)
- `parallel-iters`: [references/parallel-iters.md](references/parallel-iters.md)
- `parallel-agents`: [references/parallel-agents.md](references/parallel-agents.md)
- `parallel-isolated-agents`: [references/parallel-isolated-agents.md](references/parallel-isolated-agents.md)

Do not create workflow state before reading them.

## Invariants

- Before any Herdr operation, satisfy the `HERDR_ENV=1` preflight in the Herdr mechanics reference; stop outside a Herdr-managed pane.
- Herdr is authoritative for live state. Keep local records to durable contracts, pointers, stable IDs, ownership, decisions, and exceptions; never mirror transcripts or routine status.
- Put non-trivial context in agent-owned Markdown packets and send only their paths. Keep shared summaries bounded.
- Default to one agent per tab and one pane per tab. Use each created workspace's root pane for its first agent and panes only when requested.
- Check installed CLI help before relying on command syntax.
- Iterative work needs fixed completion criteria. Stop when satisfied, paused, blocked, unsafe, out of scope, or after two no-progress passes; polish alone never justifies continuation.
