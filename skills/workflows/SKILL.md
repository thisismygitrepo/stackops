---
name: workflows
description: Manage external interactive agent workflows through herdr and wt/Worktrunk isolated worktrees. Use when the user invokes handover, iter, parallel-agents, parallel-isolated-agents, asks to hand off current work, asks for recursive iterative improvement, asks for parallel agents, asks to delegate messages to herdr-managed agent sessions, or wants Codex/OpenCode/Pi/another CLI agent to continue or coordinate work.
---

# Workflows

Use this skill to coordinate external agent workflows through `herdr`, including handovers, iterative improvement chains, parallel agents, and Worktrunk-isolated parallel agents.

This skill provides four commands:

- `handover`: transfer active work to a new interactive agent session.
- `iter`: run an unbounded improvement chain where each agent performs one pass and starts the next iteration agent in the same Herdr workspace.
- `parallel-agents`: coordinate the user's external parallel agents.
- `parallel-isolated-agents`: create `wt`/Worktrunk-managed isolated worktrees and start one Herdr-managed agent per worktree.

## Load The Right Reference

Before acting, read the shared Herdr rules and the specific command reference:

- Shared Herdr rules: [references/herdr.md](references/herdr.md)
- `handover`: [references/handover.md](references/handover.md)
- `iter`: [references/iter.md](references/iter.md)
- `parallel-agents`: [references/parallel-agents.md](references/parallel-agents.md)
- `parallel-isolated-agents`: [references/parallel-isolated-agents.md](references/parallel-isolated-agents.md)

Do not start agents, create tabs, split panes, write workflow records, or create worktrees until the relevant reference files have been read.

## Shared Invariants

Use `herdr` as the process and session coordinator. `herdr` is the source of truth for external agent sessions, status, pane output, and live metadata.

Keep project files small and durable. Store stable identifiers, worktree ownership, iteration records, and exceptional notes only where the command reference requires them. Do not mirror Herdr status, full transcripts, message timestamps, result timestamps, or routine activity into local JSON or Markdown.

Use pointer-first cross-agent communication. For any non-trivial delegated context, write a Markdown packet under the workflow run directory and send the agent only a short Herdr prompt that points to the packet path. Each agent owns its own record directory; shared files must stay bounded summaries and pointer indexes.

Keep the distinction between tabs/windows and panes explicit. Herdr exposes top-level terminal targets as `tab` resources inside a `workspace`; treat a user request for tabs or windows as one Herdr tab per agent unless the installed CLI exposes a separate window concept. A pane is only a split inside one tab/window.

Use one agent per separate Herdr tab by default, or one named `herdr` session per agent when workspace/tab commands are unavailable. Do not put multiple agents into panes inside one tab/window unless the user explicitly asks for a pane-based layout.

Check `herdr --help` and relevant subcommand help before relying on a command shape. When installed help differs from examples in the references, preserve these invariants and use the installed command surface.
