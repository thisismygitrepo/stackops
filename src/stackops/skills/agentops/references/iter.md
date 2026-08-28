# Iter

Read [Herdr mechanics](herdr.md) first. `iter` runs one focused pass per agent and launches a successor only when fixed completion criteria remain unmet and another material pass is credible.

## Contract

Before launch, define the objective, observable completion criteria, evaluation method, constraints, and work class:

- `functionality`: use whenever end-user behavior remains incomplete. Each pass must advance production behavior. Tests, coverage, validation infrastructure, lint/type-only work, refactors, docs, audits, cleanup, and speculative hardening are out of scope and are not progress unless explicitly requested. After implementation, run at most one existing focused check; do not chase unrelated failures.
- `quality`: use only when the user explicitly requests non-functional work such as tests, coverage, benchmarks, validation, refactoring, docs, hardening, or cleanup.

Do not invent quality gates. Stop when criteria are satisfied, the user pauses, work is blocked/unsafe/out of scope, a functionality pass has no production delta, or two consecutive passes make no material progress. Polish alone never justifies continuation.

Use internal sub-agents only for independent implementation chunks that directly advance the objective; never for unrequested audits, tests, benchmarks, reviews, or alternatives.

Interactive mode is the default. Preserve the selected mode across passes.

## Start

1. Complete the Herdr preflight. Inspect Herdr help, require Herdr 0.8.2/protocol 20, inspect repository state, project rules, branch/commit, changed files, prior commands, and blockers. Record `HERDR_SESSION`, using `default` only when unset.
2. Create `.ai/agentops/iterations/<slug>/` and write the records below before launch.
3. Create one Herdr workspace, rename its returned root tab `iter-<slug>-001`, and launch the autonomous agent in its returned root pane with `agent start --kind ... --pane ...`. Do not create another initial tab.
4. Send `Read <records>/iter-001/task.md and follow it. Do not assume access to prior conversation.` with `agent prompt --wait` and confirm its returned lifecycle state. Do not send another Enter.
5. Report the slug, records path, workspace, agent target/status, and mode.

Use `iter-<slug>` for the workspace and `iter-<slug>-<NNN>` for tabs and agents. Keep `<slug>` to at most 23 allowed name characters so the live agent name remains valid. In non-interactive mode, use the CLI's documented one-shot form through `pane run`; if it cannot launch a successor, the controller does so from the written recommendation.

Write `run.json` immediately after workspace creation:

```json
{
  "schema_version": 1,
  "herdr_version": "0.8.2",
  "herdr_protocol": 20,
  "herdr_session": "default",
  "workspace_id": "w1",
  "workspace_label": "iter-<slug>"
}
```

## Records

```text
.ai/agentops/iterations/<slug>/
  run.md
  run.json
  state.md
  index.md
  iter-<NNN>/
    task.md
    result.md
    recommendation.md
    handoff.json          # continuing passes only
```

- `run.md`: stable objective, work class, functional criteria, explicitly permitted non-functional work, exclusions, completion criteria, evaluation, mode, workspace, agent kind/native arguments, boundaries, project rules, and the pass protocol below.
- `state.md`: bounded current result, criteria status, risks/blockers, no-progress count, and anti-repeat notes.
- `index.md`: one compact row per pass with Herdr target, packet paths, production delta, focused check, and outcome.
- `result.md`: production behavior/files changed, commands/check, criteria status, risks, and state/index updates.
- `recommendation.md`: the compact decision described below.

Each agent reads only `run.md` and its own `task.md`. It may read specific older records only to verify a fact, blocker, or duplicate idea; never bulk-read prior passes. Keep shared files bounded and do not store transcripts.

Put this pass protocol in `run.md`:

- Do one focused pass after verifying local state. Treat the previous recommendation as a hypothesis.
- Target the highest-impact unmet criterion and resize the next pass when evidence warrants it; never continue by inertia.
- In functionality mode, obey its exclusions and require a direct production delta. A pass without one stops without a successor.
- Run at most the permitted focused check. Do not create validation infrastructure or chase unrelated failures.
- Evaluate every completion criterion unchanged. Write `result.md`, `recommendation.md`, the `index.md` row, and changed shared state.
- Stop without successor artifacts when a stop condition applies.
- When continuing, recommend one pass toward an unmet criterion, write its `task.md`, then close pass `<NNN-1>`'s tab if present. Create pass `<NNN+1>` with `tab create`, launch it in the returned root pane, send only its task path with `agent prompt --wait`, confirm the lifecycle result, query both agents, then write the exact handoff receipt.

## Task Packet

```text
# Iteration <NNN> Task

Run records: <path>

Read first:
- run.md
- iter-<NNN>/task.md

Previous recommendation:
<short recommendation, or "none">

Current focus:
<one implementation direction toward an unmet criterion>

Optional detail pointers:
<specific paths, or "none">

Expected report:
<production delta, files changed, focused check if any, criteria status, decision, blocker or successor status>
```

## Handoff Receipt

Write `iter-<NNN>/handoff.json` only after the successor prompt is visibly accepted. Use the active session plus fresh `herdr api snapshot` and `herdr agent get` values:

```json
{
  "schema_version": 1,
  "herdr_version": "0.8.2",
  "herdr_protocol": 20,
  "herdr_session": "default",
  "workspace_id": "w1",
  "source_iteration": 1,
  "source_tab_id": "w1:t1",
  "successor_iteration": 2,
  "successor_tab_id": "w1:t2",
  "successor_pane_id": "w1:p2",
  "successor_terminal_id": "term_...",
  "successor_agent_name": "iter-<slug>-002",
  "accepted_revision": 42
}
```

Never infer, pre-create, copy, or repair a receipt. Its identifiers and accepted revision must match a fresh atomic Herdr snapshot captured after `agent prompt` accepted the successor task.

## Recommendation

Keep `recommendation.md` to 5-10 lines:

- `complete`, `stopped`, or `continuing`
- production delta; `none` stops a functionality run
- criterion status and decisive evidence
- one credible next pass only when continuing, including scope calibration
- focused-check signal and any risk/blocker that changes the decision
- specific detail pointers only when needed

Copy it inline into the successor task; do not copy older recommendations, transcripts, or command output.
