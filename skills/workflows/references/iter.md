# Iter

Use `iter` when the user asks for an agent, or a chain of agents, to work toward an improvement goal across successive generations. Typical goals include performance targets, quality targets, benchmark improvements, bug-count reductions, UX polish, test coverage, or any task where an agent may make progress, evaluate whether the goal is fully reached, and hand off credible remaining ideas to a later agent.

Read [herdr.md](herdr.md) before using this command.

## Contents

- [Core Protocol](#core-protocol)
- [Required Behavior](#required-behavior)
- [Iteration Records](#iteration-records)
- [Herdr Naming And Layout](#herdr-naming-and-layout)
- [Iteration Agent Prompt Format](#iteration-agent-prompt-format)
- [Handoff Requirements](#handoff-requirements)
- [Failure Handling](#failure-handling)

## Core Protocol

`iter` starts a normal external agent through `herdr`, not an internal subagent. Each iteration agent owns one numbered generation.

At the end of its generation, the agent must either stop because the success criteria are reached, stop because it is blocked or has no credible next ideas, or start the next numbered agent in the same Herdr workspace with a complete handoff.

A continuation requires evidence and a concrete hypothesis. Do not spawn another agent only because the result is imperfect.

The user may specify whether spawned agents are interactive or non-interactive. The default is interactive. Preserve the selected mode for later iterations unless the user explicitly changes it.

## Required Behavior

1. Identify the objective, success criteria, and constraints. If the objective is missing, ask before starting. If the success criteria are vague but the direction is clear, write a concrete working interpretation into the iteration records and prompts instead of blocking.
2. Determine the agent mode:
   - `interactive` by default, using the same interactive CLI as the controller unless the user asks for another agent type.
   - `non-interactive` only when the user asks for agents that exit when done, or when the selected agent has no interactive mode.
3. Inspect `herdr --help` and relevant workspace/tab/window/pane/session/help commands before creating the first agent. For non-interactive mode, also inspect the target agent CLI help or documentation available locally to find the correct one-shot invocation.
4. Capture fresh local context: current working directory, repository root, branch, commit, status, changed files, relevant commands already run, project rules, and known blockers.
5. Create a short slug from the goal and a records root:

```text
.ai/workflows/iterations/<descriptive-slug>/
```

6. Create or update root-level iteration records before launching the first agent. Use Markdown by default. Do not mirror full Herdr transcripts, routine timestamps, or live statuses into local files; Herdr remains the activity ledger.
7. Launch `iter-001` in one Herdr workspace dedicated to this chain. Use one Herdr tab/window per iteration agent with exactly one pane by default. Treat a user request for a "window" as a Herdr tab unless the installed CLI exposes a separate window concept.
8. Send the first agent a complete instruction using the Iteration Agent Prompt Format below.
9. Tell the user the slug, records path, Herdr workspace, first agent target, visible status, and mode.

## Iteration Records

Keep durable knowledge under `.ai/workflows/iterations/<descriptive-slug>/`. The exact document names may vary when a project has a better convention, but every chain must keep the following information easy for later agents to find:

- root overview: original objective, interpreted success criteria, selected mode, Herdr workspace, controller agent command, shared constraints, current best result, and where to look for per-iteration records
- attempt ledger: compact list of tried ideas, hypotheses, measurements, outcomes, and "do not repeat unless..." notes across the chain
- per-iteration directory: `.ai/workflows/iterations/<descriptive-slug>/iter-001/`, `.ai/workflows/iterations/<descriptive-slug>/iter-002/`, and so on
- per-iteration brief: what this agent received, what local state it verified, and what direction it chose
- per-iteration results: files changed, commands run, benchmark or validation evidence, whether success criteria were reached, and known regressions or risks
- per-iteration handoff: only when continuing, the next iteration prompt or the essential content to include in it

Prefer names like:

```text
.ai/workflows/iterations/<descriptive-slug>/run.md
.ai/workflows/iterations/<descriptive-slug>/attempts.md
.ai/workflows/iterations/<descriptive-slug>/iter-001/brief.md
.ai/workflows/iterations/<descriptive-slug>/iter-001/results.md
.ai/workflows/iterations/<descriptive-slug>/iter-001/handoff.md
```

Before choosing a direction, every iteration agent must read the root overview, the attempt ledger, and at least the previous two `iter-*` directories when they exist.

The handoff to the next generation must include enough history to avoid repeating ideas from the current iteration and the previous two iterations. Retrying an older or failed idea is allowed only when the agent states the new evidence, changed implementation detail, or materially different variant that makes the retry worthwhile.

## Herdr Naming And Layout

Use stable names that include the iteration number:

```text
workspace/tab label: iter-<descriptive-slug>
agent/tab name:      iter-<descriptive-slug>-001
next agent/tab name: iter-<descriptive-slug>-002
```

If names would become too long, shorten the slug but keep the `iter-` prefix and three-digit iteration number.

Later agents must start the next agent in the same Herdr workspace. They may create a new tab/window in that workspace, but they must not split an existing tab into panes unless the user explicitly requested a pane-based layout.

Known interactive command shape:

```bash
herdr workspace create --cwd '<cwd>' --label 'iter-<descriptive-slug>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label 'iter-<descriptive-slug>-001' --no-focus
herdr agent start 'iter-<descriptive-slug>-001' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <agent argv...>
herdr agent send 'iter-<descriptive-slug>-001' '<iteration prompt>'
herdr agent list
herdr tab list --workspace '<workspace_id>'
herdr pane list --workspace '<workspace_id>'
```

For non-interactive mode, still keep the process visible through Herdr. Prefer the target CLI's documented one-shot invocation inside a Herdr-managed pane or agent target. The command should exit when done.

If the one-shot command cannot itself launch the next generation, the controller that collects its output must create the next agent from the written handoff documents.

## Iteration Agent Prompt Format

```text
You are iteration <NNN> in an iterative improvement chain managed by the workflows iter command.

Goal:
<original user objective>

Success criteria:
<measurable target or explicit working interpretation>

Mode:
<interactive | non-interactive>. Preserve this mode when starting the next iteration unless the user changes it.

Current directory:
<absolute path>

Herdr workspace:
<workspace id or name; all later iterations must use this same workspace>

Iteration records:
<absolute or repo-relative path to .ai/workflows/iterations/<slug>/>

Project/session rules:
<critical rules about edits, tests, commits, deployment, privacy, or tools>

History to read before acting:
- Root overview and attempt ledger.
- At least the two previous iter-* directories when they exist.
- The current handoff, if this is not iter-001.

Anti-repeat requirement:
Do not repeat ideas attempted in the current or previous two iterations unless you state what materially changed and why the retry is justified.

Your task:
1. Verify local state before editing.
2. Read the iteration records listed above.
3. Choose a focused direction. You may follow the suggested handoff ideas or investigate a better direction if the records support it.
4. Make the improvement, keeping changes scoped to the goal.
5. Measure or validate the result with the strongest practical evidence.
6. Update this iteration's records under iter-<NNN>/.
7. Update the root attempt ledger with attempted ideas, outcomes, evidence, and do-not-repeat notes.
8. If the success criteria are reached, write final results and do not start another agent.
9. If the success criteria are not reached but credible next ideas remain, write iter-<NNN>/handoff.md, start iter-<NNN+1> in the same Herdr workspace with a tab/window name that includes the next iteration number, submit a complete prompt that includes this protocol and the necessary history, then report what you launched.
10. If you are blocked or have no credible next ideas, write final results and do not start another agent.

Do not assume access to the original conversation. Use Herdr for agent coordination and the iteration records for durable context.
```

## Handoff Requirements

The handoff to the next agent must include:

- the original goal and success criteria
- current best result and how it was measured
- files changed and commands run in the current iteration
- ideas attempted in the current iteration and the previous two iterations, with outcomes
- known bad or low-value directions to avoid
- two to five credible next ideas, ranked when possible
- permission for the next agent to choose a different direction after reading the records
- the same stop/continue protocol, including the requirement to start `iter-<NNN+1>` only when there are credible next ideas
- mode-specific launch instructions for interactive or non-interactive agents

## Failure Handling

If `herdr` is unavailable, the agent command cannot be identified, a workspace/tab/agent cannot be created, or the prompt cannot be submitted, report the exact failure and write the prepared prompt into the iteration records.

Do not claim an iteration agent exists unless Herdr shows it. If local records cannot be written, stop and report the failure rather than starting an agent without durable context.
