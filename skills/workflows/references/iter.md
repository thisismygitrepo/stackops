# Iter

Use `iter` when the user wants an agent chain to keep improving a goal across generations. Good fits: performance, quality, benchmarks, bug reduction, UX polish, coverage, simplification, or any objective where each generation can make one focused pass and hand off. Read [herdr.md](herdr.md) first.

`iter` starts normal external agents through Herdr. Each generation owns one numbered pass and must start the next numbered agent in the same Herdr workspace before considering its pass complete.

Do not let an iteration stop because tests pass, criteria appear satisfied, no obvious idea remains, or the work looks good. Valid stops are only explicit external stop/pause, launch failure, concrete blocker, or scope/safety violation.

Default mode is interactive. Use non-interactive only when the user asks or the selected agent has no interactive mode. Preserve the chosen mode across generations.

## Improvement Bias

Each generation must leave the project easier for later generations to improve. Prefer small files, clear boundaries, typed/structured interfaces, deterministic validation, and project-native extension points.

Avoid hidden global state, broad rewrites without stable boundaries, duplication, long functions, magic configuration, tangled imports, implicit data contracts, and speculative abstractions. Prefer modest structural cleanup over a narrow local fix when it unlocks safer later work and can be validated.

## Startup

1. Identify objective, evaluation criteria, and constraints. Ask only if the objective is missing; otherwise write a concrete working interpretation into the records.
2. Select mode: interactive by default, non-interactive only when requested or required.
3. Inspect `herdr --help` and relevant workspace/tab/pane/agent help. For non-interactive mode, inspect the target CLI help for one-shot invocation.
4. Capture cwd, repo root, branch, commit, status, changed files, relevant commands already run, project rules, and blockers.
5. Create records under:

```text
.ai/workflows/iterations/<descriptive-slug>/
```

6. Write the root records and `iter-001/task.md` before launch.
7. Launch `iter-001` in a dedicated Herdr workspace with one tab and one pane.
8. Send only a short Herdr bootstrap prompt pointing to `iter-001/task.md`.
9. Report slug, records path, Herdr workspace, first agent target, visible status, and mode.

## Records

Keep durable context under `.ai/workflows/iterations/<slug>/`:

- `run.md`: stable contract with objective, evaluation criteria, mode, Herdr workspace, controller command, autonomous argv, workdir boundaries, project rules, and continuation rules.
- `state.md`: bounded rolling state with current best result, active risks, blockers, anti-repeat notes, and useful next directions. Rewrite or compact this file each pass; do not append indefinitely.
- `index.md`: one compact row per iteration with Herdr target, packet paths, result path, handoff path, files touched, validation, and short outcome.
- `iter-001/task.md`: the task packet addressed to that iteration.
- `iter-001/notes.md`: optional local notes for that iteration; not required reading for later iterations.
- `iter-001/result.md`: files changed, commands run, validation evidence, criteria status, risks, and state/index updates made.
- `iter-001/handoff.md`: the packet from this iteration to the next one. It must point to relevant records instead of copying old handoffs.

Do not maintain a growing prompt transcript in Markdown. Do not paste prior handoffs into the next prompt. The Markdown packet is the source of truth; the Herdr prompt points to it.

Every iteration reads only:

- `run.md`
- `state.md`
- its own `iter-<NNN>/task.md`
- the immediately previous `iter-<NNN-1>/handoff.md`, when the task packet points to it

An iteration may open older records only when `state.md`, `index.md`, or the incoming handoff points to a specific file, or when it needs to verify a suspected duplicate idea. It must not bulk-read all prior `iter-*` directories.

## Naming And Launch

Use names with the iteration number:

```text
workspace/tab label: iter-<slug>
agent/tab name:      iter-<slug>-001
next agent/tab name: iter-<slug>-002
```

Keep the `iter-` prefix and three-digit number if shortening is needed.

Interactive command shape:

```bash
herdr workspace create --cwd '<cwd>' --label 'iter-<slug>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label 'iter-<slug>-001' --no-focus
herdr agent start 'iter-<slug>-001' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <autonomous agent argv...>
herdr agent send 'iter-<slug>-001' 'Read <records>/iter-001/task.md and follow it. Do not assume access to prior conversation.'
herdr pane send-keys '<pane_id>' Enter
herdr agent list
herdr tab list --workspace '<workspace_id>'
herdr pane list --workspace '<workspace_id>'
```

For non-interactive mode, run the target CLI's documented one-shot invocation through Herdr. If the one-shot agent cannot launch the next generation itself, the controller that reads its written handoff must launch the next agent from the packet path.

## Task Packet

Each `iter-<NNN>/task.md` must be standalone enough to bootstrap that iteration without copying accumulated history:

```text
# Iteration <NNN> Task

Run records:
<absolute or repo-relative path to .ai/workflows/iterations/<slug>/>

Read first:
- run.md
- state.md
- iter-<NNN>/task.md
- iter-<NNN-1>/handoff.md, if this packet names one

Incoming handoff:
<path to previous handoff, or "none for iter-001">

Current focus:
<one focused improvement direction, or instruction to independently inspect within scope>

Hard rules:
- Do exactly one focused improvement pass.
- Verify local state before editing.
- Validate with the strongest practical evidence.
- Update state.md, index.md, iter-<NNN>/result.md, and iter-<NNN>/handoff.md.
- Create iter-<NNN+1>/task.md before launching the next agent.
- Start iter-<NNN+1> in the same Herdr workspace and submit only a short prompt pointing to its task packet.
- Never stop because criteria look satisfied or no obvious idea remains.
- Stop only for explicit external stop/pause, launch failure, concrete blocker, or scope/safety violation.

Expected final report:
<changes made, validation run, next Herdr target/status, blockers if any>
```

## Handoff Packet

The handoff to the next agent is a file, not a large Herdr prompt. `iter-<NNN>/handoff.md` must include:

- current iteration summary
- files changed and validation evidence from this iteration
- state/index updates made
- current best result and active risks
- bad or low-value directions to avoid
- credible next ideas, or instruction to independently inspect for marginal improvements
- specific older record paths only when the next agent truly needs them
- mode-specific launch instructions
- the same unbounded continuation protocol

The handoff must not include prior handoffs verbatim, full command output, full Herdr transcripts, or a copied list of every previous iteration.

Before launching `iter-<NNN+1>`, write `iter-<NNN+1>/task.md` that points to `run.md`, `state.md`, and `iter-<NNN>/handoff.md`. Then submit a short prompt:

```text
Read <records>/iter-<NNN+1>/task.md and follow it. Do not assume access to prior conversation.
```

When starting the next iteration, prompt text in a terminal is not enough. Send explicit `Enter`, confirm Herdr status/recent output shows acceptance, and only then finish the current pass.
