# Herdr Mechanics

Read this before any workflow command. `herdr` is the live ledger for external agent process state, terminal output, pane metadata, and prompt delivery.

## Preflight

Before inspecting or controlling Herdr, verify that the controller is itself running in a Herdr-managed pane:

```bash
test "${HERDR_ENV:-}" = 1
```

If this fails, say that AgentOps requires a Herdr-managed pane and stop. Do not inspect or control the focused default session from outside Herdr.

The installed binary is authoritative. Use `herdr --help`, then run the relevant command group without a subcommand:

```bash
herdr workspace
herdr tab
herdr pane
herdr agent
herdr worktree
herdr notification
herdr integration
herdr session
```

Do not run bare `herdr` for discovery because it launches or attaches the TUI. Do not probe a mutating nested command by omitting arguments; creation commands execute with defaults.

AgentOps iteration maintenance tracks the current Herdr CLI; there is no pinned version. Confirm the live server with `herdr status` and the active contract with `herdr api snapshot` before creating iteration records. StackOps validates the returned snapshot shape itself and rejects an incompatible server loudly.

## Targets And State

Public workspace, tab, and pane IDs are opaque stable handles. Parse them from JSON responses instead of deriving them from sidebar order or examples. Herdr injects caller context into managed panes:

```bash
printf '%s\n' "$HERDR_WORKSPACE_ID" "$HERDR_TAB_ID" "$HERDR_PANE_ID"
```

Prefer `--current` when targeting the calling pane and explicit IDs or unique agent names everywhere else. Omitting a target can act on another client's focused pane.

Agent commands accept a unique live agent name or the pane ID currently hosting that agent. They do not accept terminal IDs or bare agent-kind labels. Names must match `[a-z][a-z0-9_-]{0,31}` and be unique among live agents. A name follows its pane occupant and is cleared when that agent exits, is released, or is replaced.

Herdr lifecycle states have specific meanings:

- `idle`: ready for input and already seen in the focused Herdr UI.
- `done`: ready for input after unseen background work finished.
- `blocked`: Herdr recognized an approval or question UI.
- `working`: active agent work.
- `unknown`: an agent is present but Herdr cannot classify it confidently; this does not prove completion.

Focusing the tab or using a pane/agent focus command marks work seen. CLI reads do not.

## Launch

Interactive `agent start` requires an existing available shell pane. It does not create, split, or move layout. Set the cwd when creating the workspace, tab, or pane, parse the returned root pane, then start the requested kind:

```bash
herdr workspace create --cwd '<cwd>' --label '<workflow-name>' --no-focus
herdr tab rename '<root-tab-id>' '<agent-name>'
herdr agent start '<agent-name>' --kind '<kind>' --pane '<root-pane-id>' -- <native-agent-args...>
```

`workspace create` returns `.result.workspace`, `.result.tab`, and `.result.root_pane`. `tab create` returns `.result.tab` and `.result.root_pane`. Use the workspace's root tab/pane for the first agent; do not create an extra initial tab. Both accept `--env <KEY=VALUE>` to set environment variables for the launched shell process.

For each later one-pane tab:

```bash
herdr tab create --workspace '<workspace-id>' --cwd '<cwd>' --label '<agent-name>' --no-focus
herdr agent start '<agent-name>' --kind '<kind>' --pane '<returned-root-pane-id>' -- <native-agent-args...>
```

Pass only native agent arguments after `--` because Herdr selects the executable from `--kind`. Unless the user requests inspect-only or supervised execution, use the target CLI's autonomous permission arguments:

- Codex: `--dangerously-bypass-approvals-and-sandbox --cd '<workdir>'`
- OpenCode: `run --interactive --dangerously-skip-permissions --dir '<workdir>'`
- Pi: `--approve`

Inspect `herdr agent` for the installed kind list and the target CLI's own help for its arguments. A successful `agent start` waits for the expected agent to become interactively ready. If startup returns `agent_not_ready` because the agent is blocked, the name remains usable; inspect it and wait for an idle state before prompting.

Use `pane run` only for an ordinary command or an intentionally non-interactive agent invocation:

```bash
herdr pane run '<pane-id>' '<command>'
herdr pane wait-output '<pane-id>' --match '<text>' --timeout <ms>
```

## Current Command Shapes

```bash
herdr workspace list
herdr workspace create --cwd '<cwd>' --label '<name>' --no-focus
herdr workspace close '<workspace-id>'
herdr tab list --workspace '<workspace-id>'
herdr tab create --workspace '<workspace-id>' --cwd '<cwd>' --label '<name>' --no-focus
herdr tab rename '<tab-id>' '<name>'
herdr tab close '<tab-id>'
herdr pane list --workspace '<workspace-id>'
herdr pane current --current
herdr pane layout --pane '<pane-id>'
herdr pane read '<pane-id>' --source recent-unwrapped --lines 200
herdr pane run '<pane-id>' '<command>'
herdr pane send-text '<pane-id>' '<text>'
herdr pane send-keys '<pane-id>' enter
herdr pane wait-output '<pane-id>' --match '<text>' --lines 200 --timeout <ms>
herdr pane wait-output '<pane-id>' --regex '<rust-regex>' --raw --timeout <ms>
herdr pane get '<pane-id>'
herdr pane process-info '<pane-id>'
herdr pane zoom '<pane-id>'
herdr pane report-agent '<pane-id>' --source '<workflow-source>' --agent '<label>' --state '<idle|working|blocked|unknown>' --message '<note>'
herdr pane report-agent-session '<pane-id>' --source '<workflow-source>' --agent '<label>' --agent-session-id '<id>' --agent-session-path '<path>'
herdr pane report-metadata '<pane-id>' --source '<workflow-source>' --agent '<label>' --title '<title>' --token workflow=agentops
herdr pane release-agent '<pane-id>' --source '<workflow-source>' --agent '<label>'
herdr pane close '<pane-id>'
herdr agent list
herdr agent get '<agent-target>'
herdr agent read '<agent-target>' --source recent-unwrapped --lines 200
herdr agent prompt '<agent-target>' '<text>' --wait --timeout <ms>
herdr agent rename '<agent-target>' '<new-name>'
herdr agent focus '<agent-target>'
herdr agent attach '<agent-target>'
herdr agent send-keys '<agent-target>' esc
herdr agent wait '<agent-target>' --timeout <ms>
herdr agent explain '<agent-target>' --json
herdr workspace report-metadata '<workspace-id>' --source '<workflow-source>' --token workflow=agentops
```

`pane report-metadata` supports title, display-agent, state-label, and token metadata; `workspace report-metadata` supports token metadata only. Neither has a `--custom-status` option. Report commands accept `--seq <N>` for ordering and `--ttl-ms <N>` to expire display-only metadata, and `report-agent-session` additionally accepts `--session-start-source`. Top-level `herdr wait` no longer exists. Use `agent wait` for lifecycle state and `pane wait-output` for terminal text.

Use stable report sources such as `agentops:<run-id>:<agent-id>`.

## Prompt, Wait, And Read

Submit interactive work atomically through the agent surface:

```bash
herdr agent prompt '<agent-target>' 'Read <packet-path> and follow it. Do not assume access to prior conversation.' --wait --timeout 120000
```

`agent prompt` sends bracketed-paste-aware text and Enter. Do not follow it with `pane send-keys enter`. It rejects an already blocked agent before writing input. With `--wait` and no `--until`, it waits for the first settled `idle`, `done`, or `blocked` state. Use `--until` only when the workflow requires a specific state. A non-working target must show a lifecycle change within five seconds or Herdr returns `agent_prompt_stalled`.

If a wait fails or returns `blocked`, inspect `agent get` and `agent read`. Do not answer an approval or question dialog without the user's direction. When `unknown` is returned, inspect output instead of treating it as completion.

Prefer `recent-unwrapped` for logs and transcripts. `visible` is the current viewport, `recent` retains soft wraps, and agent `detection` exposes the bottom-buffer text used for classification. Use `--format ansi` only when styling is evidence.

Alternate-screen rows that leave the screen do not enter Herdr's host scrollback. If increasing `--lines` cannot recover a complete response, ask the agent to write its result to the workflow result packet and read that file directly.

## Records

Local workflow files are durable contracts and cross-agent packets, not a second transcript.

Use pointer-first communication:

- Write non-trivial task, result, handoff, and review context to Markdown under the workflow run directory.
- Send agents a short Herdr prompt that names the packet path and the action to take.
- Do not paste the same long context into both the Herdr prompt and Markdown records.
- Do not make later agents read every previous agent directory. They read the shared run contract and the packet addressed to them. They read bounded shared state or older records only when the workflow reference requires it or the addressed packet points to a specific file.

Use agent-owned directories for Markdown records:

```text
.ai/agentops/<operation>/<run-id>/
  run.md
  state.md
  index.md
  agents/<agent-id>/
    task.md
    result.md
    handoff.md
```

Keep shared files bounded:

- `run.md`: stable objective, scope, mode, workspace, agent kind/arguments, and constraints.
- `state.md`: current best state, active blockers, anti-repeat notes, and next useful directions. Rewrite or compact it instead of appending indefinitely.
- `index.md`: one compact row per agent or iteration with pointers to that agent's packets and short outcome.

Local JSON stores Herdr targets, delegated roles, worktree ownership, packet paths, and lifecycle exceptions Herdr cannot represent. Do not mirror live status, full prompts, transcripts, command output, or routine timestamps. Re-query Herdr for current state.

## Layout And Safety

Use Herdr's persistent `default` session and create workflow workspaces within it. Use another session only when the user explicitly requests one.

Default AgentOps layout is one agent per tab and one pane per tab. Use the root tab/pane for the first agent and `tab create` for each later agent. Use `pane split` only when the user explicitly requests a pane layout; choose direction after inspecting `pane layout` and keep the caller focused with `--no-focus`.

- Use `--no-focus` for background work.
- Do not close workspaces, tabs, panes, or sessions the workflow did not create unless the user explicitly asks.
- Never run `herdr server stop` from an active session unless the user explicitly intends to stop the server and its pane processes.
- CLI server errors are JSON on stderr with exit status 1; syntax errors exit with status 2.
