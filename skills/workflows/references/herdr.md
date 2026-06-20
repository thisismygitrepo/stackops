# Herdr Mechanics

Read this reference before using any workflow command. Use it together with the specific command reference linked from `SKILL.md`.

## Activity Ledger

Use Herdr commands for registration, status, command visibility, and short operational annotations before writing local JSON:

```bash
herdr workspace list
herdr tab list --workspace '<workspace_id>'
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
herdr pane report-agent '<pane_id>' --source '<workflow-source>' --agent '<label>' --state '<idle|working|blocked|unknown>' --message '<short note>'
herdr pane report-agent-session '<pane_id>' --source '<workflow-source>' --agent '<label>' --agent-session-id '<id>' --agent-session-path '<path>'
herdr pane report-metadata '<pane_id>' --source '<workflow-source>' --agent '<label>' --title '<short title>' --custom-status '<short status>'
herdr wait agent-status '<pane_id>' --status '<idle|working|blocked|done|unknown>' --timeout <ms>
herdr wait output '<pane_id>' --match '<text>' --lines 200 --timeout <ms>
```

Use a stable `--source` value such as `workflows:<run-id>:<agent-id>` for report commands.

Use `herdr agent start` to create registered agent targets whenever possible, then refresh with `herdr agent list`, `herdr tab list`, and `herdr pane list` instead of manually inventing IDs.

Use `herdr pane report-agent`, `herdr pane report-agent-session`, and `herdr pane report-metadata` only for state or metadata Herdr cannot infer from the agent process.

Use `herdr pane run` when the controller needs to run a shell command inside a managed pane because that keeps the command visible in Herdr scrollback. Use `herdr agent send` or `herdr pane send-text` for agent instructions, but treat them as text insertion only unless the installed `herdr` help explicitly says the selected command submits the prompt.

For interactive agent prompts, submit deliberately:

1. Wait until the target CLI is initialized and ready for input.
2. Send the instruction text with `herdr agent send <target> <text>` when a unique agent target exists, or `herdr pane send-text <pane_id> <text>` when working directly with a pane.
3. Resolve the target pane id from `herdr agent get`, `herdr agent explain --json`, or `herdr pane list`, then send `herdr pane send-keys <pane_id> Enter`.
4. Refresh status and recent output. Do not count the prompt as submitted until Herdr shows `working` or recent output clearly shows the agent accepted the prompt and began responding.
5. Before stopping, wrapping up, or claiming the spawn/delegation succeeded, verify the new agent is actually working. If the prompt text is visible but still unsubmitted, send one more explicit `Enter`, verify again, and report failure instead of claiming success if acceptance still cannot be confirmed.

## Local Records

Local JSON must stay small: record which Herdr target belongs to which delegated role, which worktree belongs to which agent, and any lifecycle exception that Herdr cannot represent.

Do not update local JSON after every send, read, wait, or observed status change. Re-query Herdr when current status, recent output, commands, or metadata are needed.

Markdown records may be used for human-readable handoffs and iteration history when a command reference requires them. Keep those records concise and focused on durable context, decisions, evidence, and next steps.

## Layout Rules

Herdr exposes top-level terminal targets as `tab` resources inside a `workspace`. Treat a user request for tabs or windows as one Herdr tab per agent unless the installed CLI exposes a separate window concept. A pane is only a split inside one tab/window.

The default layout is one agent per separate Herdr tab, or one named `herdr` session per agent when workspace/tab commands are not available.

Do not put multiple agents into panes inside one tab/window unless the user explicitly asks for that pane-based layout. If the user does ask for multiple agents as panes in one tab/window, split the screen roughly equally across panes, verify the pane count matches the requested agents through `herdr pane list` or equivalent metadata, and keep each pane tied to exactly one agent.

Before launching agents, check `herdr tab list --workspace <workspace_id>` and `herdr pane list --workspace <workspace_id>` when available. After launch, verify the target tab has exactly one pane unless the user requested panes.

Avoid `herdr agent start --split`, `herdr pane split`, or any command that would add a pane to an existing tab/window unless panes were explicitly requested.

## Help And Discovery

Inspect `herdr --help` and the relevant subcommand help before using a command shape that is not listed in the command reference.

Known command surface:

```bash
herdr --session '<short descriptive name>'
herdr workspace create --cwd '<cwd>' --label '<short descriptive name>' --no-focus
herdr tab create --workspace '<workspace_id>' --cwd '<cwd>' --label '<short descriptive name>' --no-focus
herdr agent start '<short descriptive name>' --cwd '<cwd>' --workspace '<workspace_id>' --tab '<tab_id>' --no-focus -- <agent argv...>
herdr update --handoff
herdr session list --json
herdr agent list
herdr tab list --workspace '<workspace_id>'
herdr pane list --workspace '<workspace_id>'
herdr session attach '<session name>'
herdr session stop '<session name>' --json
herdr session delete '<session name>' --json
```

If the installed CLI uses different terms, map them carefully from `herdr --help`. Preserve one-agent-per-tab by default.
