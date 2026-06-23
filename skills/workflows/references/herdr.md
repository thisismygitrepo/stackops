# Herdr Mechanics

Read this before any workflow command. `herdr` is the live ledger for external agent process state, terminal output, pane metadata, and prompt delivery.

## Launch

Managed agents are autonomous workers. Start Codex/OpenCode/Pi/CLI agents with the target workdir set explicitly and with the target CLI's no-approval/full-permission mode enabled unless the user asks for inspect-only or supervised execution.

Known autonomous argv:

```bash
codex --dangerously-bypass-approvals-and-sandbox --cd '<workdir>'
opencode run --interactive --dangerously-skip-permissions --dir '<workdir>'
pi --approve
```

Pi uses Herdr's `--cwd` to set the workdir; do not add a cwd flag to the Pi argv unless Pi adds one. If Pi status reporting is needed, install the Herdr integration first:

```bash
herdr integration install pi
```

When examples use `<autonomous agent argv...>`, substitute the matching argv. Keep the delegated prompt scoped to the requested repo/worktree, project rules, and user objective.

## Commands

Use these command families for workflow control:

```bash
herdr --help
herdr workspace create --cwd '<cwd>' --label '<name>' --no-focus
herdr workspace list
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label '<name>' --no-focus
herdr tab list --workspace '<workspace_id>'
herdr agent start '<name>' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <autonomous agent argv...>
herdr agent list
herdr agent get '<agent target>'
herdr agent read '<agent target>' --source recent --lines 200
herdr agent send '<agent target>' '<text>'
herdr agent wait '<agent target>' --status '<idle|working|blocked|unknown>' --timeout <ms>
herdr agent explain '<agent target>' --json
herdr pane list --workspace '<workspace_id>'
herdr pane read '<pane_id>' --source recent --lines 200
herdr pane run '<pane_id>' '<command>'
herdr pane send-text '<pane_id>' '<text>'
herdr pane send-keys '<pane_id>' Enter
herdr pane report-agent '<pane_id>' --source '<workflow-source>' --agent '<label>' --state '<idle|working|blocked|unknown>' --message '<note>'
herdr pane report-agent-session '<pane_id>' --source '<workflow-source>' --agent '<label>' --agent-session-id '<id>' --agent-session-path '<path>'
herdr pane report-metadata '<pane_id>' --source '<workflow-source>' --agent '<label>' --title '<title>' --custom-status '<status>'
herdr wait agent-status '<pane_id>' --status '<idle|working|blocked|done|unknown>' --timeout <ms>
herdr wait output '<pane_id>' --match '<text>' --lines 200 --timeout <ms>
herdr tab close '<tab_id>'
herdr pane close '<pane_id>'
```

Inspect `herdr --help` and relevant subcommand help before using a command shape not listed here. Use stable report sources like `workflows:<run-id>:<agent-id>`.

## Prompt Submission

For interactive agents:

1. Wait until the target CLI is ready.
2. Send text with `herdr agent send` when a unique agent target exists; otherwise use `herdr pane send-text`.
3. Resolve the pane id from `herdr agent get`, `herdr agent explain --json`, or `herdr pane list`.
4. Send `herdr pane send-keys '<pane_id>' Enter`.
5. Confirm Herdr shows `working` or recent output shows the prompt was accepted. If the text is still sitting in the input line, send one more `Enter` and verify again.

Do not report a spawn, delegation, handoff, or iteration as complete until prompt acceptance is visible.

## Records

Local workflow files are durable contracts and cross-agent packets, not a second transcript.

Use pointer-first communication:

- Write non-trivial task, result, handoff, and review context to Markdown under the workflow run directory.
- Send agents a short Herdr prompt that names the packet path and the action to take.
- Do not paste the same long context into both the Herdr prompt and Markdown records.
- Do not make later agents read every previous agent directory. They read the shared run contract and the packet addressed to them. They read bounded shared state or older records only when the workflow reference requires it or the addressed packet points to a specific file.

Use agent-owned directories for Markdown records:

```text
.ai/workflows/<workflow>/<run-id>/
  run.md
  state.md
  index.md
  agents/<agent-id>/
    task.md
    result.md
    handoff.md
```

Workflow references may use a more specific directory name such as `iter-001/`, but the ownership rule is the same: each agent writes its own directory and only updates bounded shared files named by the workflow reference.

Keep shared files bounded:

- `run.md`: stable objective, scope, mode, workspace, launch argv, and constraints.
- `state.md`: current best state, active blockers, anti-repeat notes, and next useful directions. Rewrite or compact it instead of appending indefinitely.
- `index.md`: one compact row per agent or iteration with pointers to that agent's packets and short outcome.

Local JSON stays small: record Herdr targets, delegated roles, worktree ownership, packet paths, and lifecycle exceptions Herdr cannot represent. Do not mirror live status, full prompts, transcripts, command output, or routine timestamps. Re-query Herdr for current state.

Markdown records should preserve decisions, evidence, blockers, and next actions. Keep shell transcripts and routine activity in Herdr.

## Layout

Herdr top-level terminal targets are `tab` resources inside a `workspace`; a pane is a split inside one tab. Treat user requests for tabs or windows as one Herdr tab per agent unless installed help exposes a separate window concept.

Default layout: one agent per Herdr tab, exactly one pane per tab. Use panes only when the user explicitly requests a pane layout. Then split evenly, verify pane count, and keep exactly one agent per pane.

Avoid `herdr agent start --split`, `herdr pane split`, and any command that adds a pane to an existing tab unless panes were requested.
