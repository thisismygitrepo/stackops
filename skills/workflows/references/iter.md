# Iter

Use `iter` when the user asks for an agent, or a chain of agents, to keep improving a goal across successive generations. Typical goals include performance targets, quality targets, benchmark improvements, bug-count reductions, UX polish, test coverage, or any task where each agent can make one focused pass and then hand off to the next agent.

Read [herdr.md](herdr.md) before using this command.

## Contents

- [Core Protocol](#core-protocol)
- [Improvement-Friendly Work](#improvement-friendly-work)
- [Required Behavior](#required-behavior)
- [Iteration Records](#iteration-records)
- [Herdr Naming And Layout](#herdr-naming-and-layout)
- [Iteration Agent Prompt Format](#iteration-agent-prompt-format)
- [Handoff Requirements](#handoff-requirements)
- [Failure Handling](#failure-handling)

## Core Protocol

`iter` starts a normal external agent through `herdr`, not an internal subagent. Each iteration agent owns one numbered generation.

At the end of its generation, the agent must start the next numbered agent in the same Herdr workspace with a complete handoff before it considers its own pass complete.

Do not tell an iteration agent that it may stop when criteria are satisfied, when tests pass, when the work looks good, or when no obvious next idea remains. Evaluation criteria guide the current pass and the status record, but they are not termination criteria. If a pass finds no obvious next idea, it must still launch the next agent with instructions to independently inspect for marginal improvements, simplification, stronger validation, or hidden risks.

The only valid stops are an explicit external stop/pause from the user, a Herdr/CLI launch failure, a concrete blocker that makes the next iteration impossible, or a scope/safety violation that would make continuing wrong.

The user may specify whether spawned agents are interactive or non-interactive. The default is interactive. Preserve the selected mode for later iterations unless the user explicitly changes it.

## Improvement-Friendly Work

Because `iter` is an infinite improvement chain, each generation must leave the project easier for the next generation to change. Treat maintainability and future editability as part of the objective, not as optional polish.

Prefer changes that preserve or improve:

- small, focused files and modules instead of accumulating large catch-all files
- clear boundaries between parsing, state, side effects, UI, persistence, integration, and domain logic
- typed or structured interfaces that make downstream breakage visible to static analysis
- decoupled design that allows later agents to replace one strategy without rewriting unrelated code
- simple extension points that match existing project patterns without speculative frameworks
- deterministic validation so later agents can tell whether they improved or regressed the work

Avoid changes that make the next iteration harder: hidden global state, broad rewrites without a stable boundary, duplicated logic, long functions, magic configuration, tangled imports, implicit data contracts, or one-off abstractions that later agents cannot safely extend.

If an iteration must choose between a narrow local fix and a modest structural cleanup that unlocks safer future improvements, prefer the structural cleanup when it stays within scope and can be validated.

## Required Behavior

1. Identify the objective, evaluation criteria, and constraints. If the objective is missing, ask before starting. If the evaluation criteria are vague but the direction is clear, write a concrete working interpretation into the iteration records and prompts instead of blocking.
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
7. Launch `iter-001` with autonomous launch argv in one Herdr workspace dedicated to this chain. Use one Herdr tab/window per iteration agent with exactly one pane by default. Treat a user request for a "window" as a Herdr tab unless the installed CLI exposes a separate window concept.
8. Send the first agent a complete instruction using the Iteration Agent Prompt Format below. Follow the shared Herdr prompt submission protocol: send the text, send an explicit `Enter` key to the target pane, and verify the agent accepted it.
9. After submitting the prompt, verify the agent is actually running before reporting success: refresh the Herdr target, read recent output, and wait for a visible `working` status or other clear evidence that the prompt was accepted and execution started. If the prompt appears to be sitting unsubmitted in the terminal input line, send one more explicit `Enter`, then verify again.
10. Tell the user the slug, records path, Herdr workspace, first agent target, visible status, and mode.

## Iteration Records

Keep durable knowledge under `.ai/workflows/iterations/<descriptive-slug>/`. The exact document names may vary when a project has a better convention, but every chain must keep the following information easy for later agents to find:

- root overview: original objective, interpreted evaluation criteria, selected mode, Herdr workspace, controller agent command, autonomous launch argv, shared constraints, current best result, future-improvement constraints, and where to look for per-iteration records
- attempt ledger: compact list of tried ideas, hypotheses, measurements, outcomes, and "do not repeat unless..." notes across the chain
- per-iteration directory: `.ai/workflows/iterations/<descriptive-slug>/iter-001/`, `.ai/workflows/iterations/<descriptive-slug>/iter-002/`, and so on
- per-iteration brief: what this agent received, what local state it verified, and what direction it chose
- per-iteration results: files changed, commands run, benchmark or validation evidence, whether evaluation criteria improved or appear satisfied, and known regressions or risks
- per-iteration handoff: the next iteration prompt or the essential content to include in it
- future-improvement notes: file-size pressure, coupling introduced or removed, extension boundaries for later changes, and design debt the next agent should consider

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
herdr agent start 'iter-<descriptive-slug>-001' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <autonomous agent argv...>
herdr agent send 'iter-<descriptive-slug>-001' '<iteration prompt>'
herdr pane send-keys '<pane_id>' Enter
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

Evaluation criteria:
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

Autonomous launch argv:
<agent command and flags used to launch this worker; use the same permission mode for the next worker>

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
5. Keep the result easy for future iterations to improve: avoid oversized files, tangled coupling, hidden state, duplicated logic, and rigid one-off designs.
6. Measure or validate the result with the strongest practical evidence.
7. Update this iteration's records under iter-<NNN>/.
8. Update the root attempt ledger with attempted ideas, outcomes, evidence, and do-not-repeat notes.
9. Record future-improvement notes: file-size pressure, coupling introduced or removed, useful boundaries, and design debt the next agent should consider.
10. If the evaluation criteria appear satisfied, record the evidence, but still prepare the next iteration so it can independently verify, simplify, harden, or find marginal improvements.
11. Write iter-<NNN>/handoff.md for iter-<NNN+1>. Include clear next ideas when available. If no obvious next idea remains, say that explicitly and instruct the next agent to independently inspect for marginal improvements, simplification, stronger validation, or hidden risks.
12. Start iter-<NNN+1> in the same Herdr workspace with a tab/window name that includes the next iteration number, submit a complete prompt that includes this protocol and the necessary history, verify the new agent is actually running before stopping or wrapping up, then report what you launched.
13. Stop only for an explicit external user stop/pause, Herdr/CLI launch failure, concrete blocker that makes continuation impossible, or scope/safety violation.

Do not assume access to the original conversation. Use Herdr for agent coordination and the iteration records for durable context.
```

When starting the next iteration, do not treat a created tab, a visible CLI prompt, or text pasted into an input line as a completed handoff. Send the prompt text, send an explicit `Enter` key to the target pane, then confirm through Herdr status and recent output that `iter-<NNN+1>` accepted the prompt and began working. If the text is present but unsubmitted, send one more explicit `Enter` and verify again. Only stop or finish after the new agent is visibly running. If this cannot be confirmed, write the failure and prepared prompt into the records instead of claiming the next iteration was launched.

## Handoff Requirements

The handoff to the next agent must include:

- the original goal and evaluation criteria
- current best result and how it was measured
- files changed and commands run in the current iteration
- ideas attempted in the current iteration and the previous two iterations, with outcomes
- future-improvement notes: file-size pressure, coupling, extension boundaries, and design debt
- known bad or low-value directions to avoid
- credible next ideas when available, or an explicit note that the next agent should independently inspect for marginal improvements
- permission for the next agent to choose a different direction after reading the records
- the same unbounded continuation protocol, including the requirement to start `iter-<NNN+1>` before reporting the pass complete
- mode-specific launch instructions for interactive or non-interactive agents

## Failure Handling

If `herdr` is unavailable, the agent command cannot be identified, a workspace/tab/agent cannot be created, or the prompt cannot be submitted, report the exact failure and write the prepared prompt into the iteration records.

Do not claim an iteration agent exists unless Herdr shows it. If local records cannot be written, stop and report the failure rather than starting an agent without durable context.
