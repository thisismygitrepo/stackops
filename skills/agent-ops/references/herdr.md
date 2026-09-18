# Herdr For Agent-Ops

Run `herdr --skill` and read its full output before any workflow command. It is the authoritative reference for Herdr mechanics: CLI discovery, targets and lifecycle state, launch, command shapes, prompt/wait/read behavior, and safety. Its content tracks the installed release, so prefer it over any remembered syntax and re-run it when herdr updates.

This file holds only the Agent-Ops overrides and additions to that builtin reference.

## Controller Scope

The builtin skill gates on `HERDR_ENV=1` and stops when the caller is not inside a Herdr-managed pane. Agent-Ops controllers ignore that gate: they run from any shell, inside or outside Herdr. Never check or require `HERDR_ENV`; always target explicit IDs discovered through the CLI.

## StackOps Preflight

Before creating iteration records, confirm the live server with `herdr status server` and the active contract with `herdr api snapshot`. StackOps validates the returned snapshot shape itself and rejects an incompatible server loudly.

## Autonomous Permission Arguments

Unless the user requests inspect-only or supervised execution, pass the target CLI's autonomous permission arguments after `--`:

- Codex: `--dangerously-bypass-approvals-and-sandbox --cd '<workdir>'`
- OpenCode: `run --interactive --dangerously-skip-permissions --dir '<workdir>'`
- Pi: `--approve`

## Workflow Reporting

Report lifecycle, session, and metadata back to Herdr so its UI reflects workflow state:

```bash
herdr pane report-agent '<pane-id>' --source '<workflow-source>' --agent '<label>' --state '<idle|working|blocked|unknown>' --message '<note>'
herdr pane report-agent-session '<pane-id>' --source '<workflow-source>' --agent '<label>' --agent-session-id '<id>' --agent-session-path '<path>'
herdr pane report-metadata '<pane-id>' --source '<workflow-source>' --agent '<label>' --title '<title>' --token workflow=agent-ops
herdr workspace report-metadata '<workspace-id>' --source '<workflow-source>' --token workflow=agent-ops
herdr pane release-agent '<pane-id>' --source '<workflow-source>' --agent '<label>'
```

Use stable report sources such as `agent-ops:<run-id>:<agent-id>`. Metadata reports accept `--seq` and `--ttl-ms`; lifecycle and session reports accept `--seq`. The metadata `--agent` guard matches the detected agent label, not its unique live name.
