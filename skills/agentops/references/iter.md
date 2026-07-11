# Iter

Use `iter` when the user wants an agent chain to keep improving a goal across generations. Good fits: performance, quality, benchmarks, bug reduction, UX polish, coverage, simplification, or any objective where each generation can make one focused pass and hand off. Read [herdr.md](herdr.md) first.

`iter` starts normal external agents through Herdr. Each generation owns one numbered pass and must start the next numbered agent in the same Herdr workspace before considering its pass complete.

Do not let an iteration stop because tests pass, criteria appear satisfied, no obvious idea remains, or the work looks good. Valid stops are only explicit external stop/pause, launch failure, concrete blocker, or scope/safety violation.

Default mode is interactive. Use non-interactive only when the user asks or the selected agent has no interactive mode. Preserve the chosen mode across generations.

## Improvement Bias

Each generation must leave the project easier for later generations to improve. Prefer small files, clear boundaries, typed/structured interfaces, deterministic validation, and project-native extension points.

Avoid hidden global state, broad rewrites without stable boundaries, duplication, long functions, magic configuration, tangled imports, implicit data contracts, and speculative abstractions. Prefer modest structural cleanup over a narrow local fix when it unlocks safer later work and can be validated.

Calibrate the next iteration's workload dynamically. If the current pass was too small to make meaningful progress, recommend a broader next pass. If it was too broad, slow, risky, or left too much unfinished, recommend a narrower next pass. The next task should stay reasonable for one focused iteration, not preserve the previous scope by inertia.

Within one iteration, use the agent's own internal sub-agent mechanism when the current agent spots a clearly parallelizable chunk of substantial work, such as independent audits, file families, benchmarks, or implementation alternatives. Keep sub-agent tasks bounded, merge their results before writing the iteration result, and do not let sub-agent coordination replace the required next-iteration launch.

## Startup

1. Identify objective, evaluation criteria, and constraints. Ask only if the objective is missing; otherwise write a concrete working interpretation into the records.
2. Select mode: interactive by default, non-interactive only when requested or required.
3. Inspect `herdr --help` and relevant workspace/tab/pane/agent help. Record `HERDR_SESSION`, using `default` only when it is unset. For non-interactive mode, inspect the target CLI help for one-shot invocation.
4. Capture cwd, repo root, branch, commit, status, changed files, relevant commands already run, project rules, and blockers.
5. Create records under:

```text
.ai/agentops/iterations/<descriptive-slug>/
```

6. Write the Markdown root records and `iter-001/task.md` before launch.
7. Create a dedicated Herdr workspace, rename its returned root tab for `iter-001`, write `run.json` from the returned stable IDs, and launch the agent in that tab. Do not create a second initial tab.
8. Send only a short Herdr bootstrap prompt pointing to `iter-001/task.md`.
9. Report slug, records path, Herdr workspace, first agent target, visible status, and mode.

## Records

Keep durable context under `.ai/agentops/iterations/<slug>/`:

- `run.md`: stable contract with objective, evaluation criteria, mode, Herdr workspace, controller command, autonomous argv, workdir boundaries, project rules, and continuation rules.
- `run.json`: active Herdr session plus the stable workspace ID and label used by maintenance commands.
- `state.md`: bounded rolling state with current best result, active risks, blockers, and anti-repeat notes. Rewrite or compact this file only when those shared facts change; do not append indefinitely.
- `index.md`: one compact row per iteration with Herdr target, task path, result path, recommendation path, files touched, validation, and short outcome.
- `iter-001/task.md`: the task packet addressed to that iteration.
- `iter-001/notes.md`: optional local notes for that iteration; not required reading for later iterations.
- `iter-001/result.md`: files changed, commands run, validation evidence, criteria status, risks, and state/index updates made.
- `iter-001/recommendation.md`: the compact recommendation from this iteration to the next one. It must point to relevant records only when the next iteration may need detail.
- `iter-001/handoff.json`: stable Herdr identifiers proving the successor prompt was accepted; written only after `iter-002` is visibly working.

Do not maintain a growing prompt transcript in Markdown. Do not paste prior recommendations into the next prompt. The Markdown packet is the source of truth; the Herdr prompt points to it.

Every iteration reads only:

- `run.md`
- its own `iter-<NNN>/task.md`

The previous iteration's recommendation must be copied into `iter-<NNN>/task.md` as a short starting hypothesis, not delegated as required reading. An iteration may open `state.md`, `index.md`, older results, or older recommendations only when it needs detail to verify the recommendation, avoid a duplicate idea, or understand a concrete blocker. It must not bulk-read all prior `iter-*` directories.

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
herdr tab rename '<returned_root_tab_id>' 'iter-<slug>-001'
herdr agent rename '<returned_root_pane_id>' 'iter-<slug>-001'
herdr pane run '<returned_root_pane_id>' '<shell-joined autonomous agent argv>'
herdr agent send 'iter-<slug>-001' 'Read <records>/iter-001/task.md and follow it. Do not assume access to prior conversation.'
herdr pane send-keys '<pane_id>' Enter
herdr agent list
herdr tab list --workspace '<workspace_id>'
herdr pane list --workspace '<workspace_id>'
```

For non-interactive mode, run the target CLI's documented one-shot invocation through Herdr. If the one-shot agent cannot launch the next generation itself, the controller that reads its written recommendation must launch the next agent from the packet path.

Write `run.json` with exactly this schema immediately after workspace creation, replacing `default` with the active named session when `HERDR_SESSION` is set:

```json
{
  "schema_version": 1,
  "herdr_session": "default",
  "workspace_id": "w1",
  "workspace_label": "iter-<slug>"
}
```

## Task Packet

Each `iter-<NNN>/task.md` must be standalone enough to bootstrap that iteration without copying accumulated history:

```text
# Iteration <NNN> Task

Run records:
<absolute or repo-relative path to .ai/agentops/iterations/<slug>/>

Read first:
- run.md
- iter-<NNN>/task.md

Previous recommendation:
<one short recommendation from iter-<NNN-1>, or "none for iter-001">

Optional detail pointers:
<specific paths only if useful; do not read these by default>

Current focus:
<one focused improvement direction, or instruction to independently inspect within scope>

Hard rules:
- Do exactly one focused improvement pass.
- Verify local state before editing.
- Treat the previous recommendation as a starting hypothesis, not a command; inspect enough to confirm it is still the best next move.
- Read optional detail pointers, state.md, index.md, or older iteration records only when they help confirm facts, understand a blocker, or avoid repeating work.
- Dynamically size the next iteration: broaden it if this pass was too small to matter, narrow it if this pass was too broad, risky, slow, or left too much unfinished.
- Before recommending the next pass, briefly reassess the overall objective: if the current direction is yielding diminishing returns while larger gaps remain, redirect the next iteration toward a higher-impact gap instead of continuing by inertia.
- When substantial work inside this pass is clearly parallelizable, use bounded internal sub-agents, then merge their findings before writing result.md.
- Validate with the strongest practical evidence.
- Write iter-<NNN>/result.md and iter-<NNN>/recommendation.md.
- Update index.md with one compact row. Update state.md only when shared best state, risks, blockers, or anti-repeat notes changed.
- Create iter-<NNN+1>/task.md before launching the next agent, and copy the recommendation into it inline.
- Before creating iter-<NNN+1>'s tab, close and confirm removal of iter-<NNN-1>'s tab when it exists; then create the successor tab in the same Herdr workspace, rename its returned root pane as the agent, run the shell-joined autonomous argv in that pane, and submit only a short prompt pointing to its task packet.
- Confirm the successor is working, query both agents with `herdr agent get`, then write the current iteration's exact `handoff.json` receipt.
- Never stop because criteria look satisfied or no obvious idea remains.
- Stop only for explicit external stop/pause, launch failure, concrete blocker, or scope/safety violation.

Expected final report:
<changes made, validation run, next Herdr target/status, blockers if any>
```

## Handoff Receipt

After the successor prompt is visibly accepted, write `iter-<NNN>/handoff.json` with exactly this schema using the active Herdr session plus values from `herdr api snapshot` and `herdr agent get`:

```json
{
  "schema_version": 1,
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

Use the successor revision observed after its status becomes `working`. Never pre-create, infer, copy, or repair a receipt. The maintenance close command treats a receipt as authorization only while every identifier still matches a fresh atomic Herdr snapshot.

## Recommendation Packet

The recommendation to the next agent is a compact file, not a large Herdr prompt. `iter-<NNN>/recommendation.md` must include:

- one recommended next move, or instruction to independently inspect for the highest-impact remaining gap
- why that move is credible
- workload calibration for the next iteration: broader, narrower, or same scope, with one short reason
- parallelization opportunity for non-communicating internal sub-agents, if one exists and is substantial enough to justify splitting work
- the latest validation signal that matters to the recommendation
- active risk or blocker only if it changes the next move
- specific detail paths only when the next agent may need them
- mode-specific launch differences only when they differ from `run.md`
- a pointer back to the unbounded continuation protocol in `run.md`

Keep it short enough to copy into the next task packet without consuming meaningful context; prefer 5-10 lines. Put full files changed, commands run, validation evidence, criteria status, and state/index updates in `iter-<NNN>/result.md`, not in the recommendation.

The recommendation must not include prior recommendations verbatim, full command output, full Herdr transcripts, or a copied list of every previous iteration.

Before launching `iter-<NNN+1>`, write `iter-<NNN+1>/task.md` that points to `run.md`, includes the previous recommendation inline, and lists optional detail paths only when useful. Then submit a short prompt:

```text
Read <records>/iter-<NNN+1>/task.md and follow it. Do not assume access to prior conversation.
```

When starting the next iteration, prompt text in a terminal is not enough. Send explicit `Enter`, confirm Herdr status/recent output shows acceptance, write `handoff.json`, and only then finish the current pass.
