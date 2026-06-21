---
name: stackops
description: Teach, execute, troubleshoot, and extend the StackOps CLI/library through direct Typer entrypoints and source-backed command maps. Use when Codex works with StackOps commands, command discovery, command implementation files, generated CLI references, or entrypoints such as devops, cloud, terminal, agents, utils, fire, preview, seek, and the stackops umbrella command.
---

# StackOps

Use this skill to move from a StackOps command request to the current Typer surface and implementation files.

## Quick Workflow

1. Choose the execution form.
- In this repository, run StackOps commands as `UV_CACHE_DIR=/tmp/uv-cache uv run <entrypoint> ...`.
- For installed usage outside the repo, use direct entrypoints: `devops`, `cloud`, `terminal`, `agents`, `utils`, `fire`, `preview`, and `seek`.
- Use `stackops <entrypoint> ...` only when the user specifically wants the umbrella dispatcher or when testing the dispatcher itself.

2. Resolve command path progressively.
- Start with a top-level command from the list below.
- Load only that command's reference page.
- Follow child reference links one command segment at a time until you reach the needed leaf.
- Verify with `<command> --help` at each command level.
- Use canonical command names only (no short aliases).
- Prefer the shortest direct entrypoint that reaches the command.

3. Use references only when they reduce search.
- Load `references/cli-map.md` for the top-level CLI index and direct entrypoints.
- Load `references/source-map.md` for the root source index.
- Load `references/commands/<command>.md` for exactly one command level, then follow links from there.
- Inspect `src/stackops/scripts/python/graph/cli_graph.json` only when aliases, full node metadata, or generated-map debugging matter.

4. Follow source, not old docs.
- Treat Typer registrations in source as the source of truth.
- If docs conflict with source, explain the mismatch and proceed with the source-backed command.

5. Map command to implementation.
- Use the current command reference page to find the file that registers or implements that command.
- Remember `stackops_entry.py` is a lazy dispatcher; most behavior lives in helper modules after the first command segment.
- When adding or changing commands, update the Typer registration and the helper implementation together, then re-check `--help`.

6. Refresh generated references after CLI shape changes.
- Follow the `devops` command reference chain to the generated-reference maintenance command, then run it from the repo root.

7. Run safely.
- Commands that install, update, configure, sync, share, mount, or edit local files may mutate system state.
- Call out side effects and require explicit confirmation for risky actions.

## Top-Level Commands

- `stackops`: umbrella dispatcher and root command index. See `references/commands/command--stackops.md`.
- `devops`: developer workstation, project management, machine setup, credentials, connectivity, and StackOps maintenance. See `references/commands/command--devops.md`.
- `cloud`: cloud sync, copy, mount, and transfer workflows. See `references/commands/command--cloud.md`.
- `terminal`: terminal session orchestration and summaries. See `references/commands/command--terminal.md`.
- `agents`: agent setup, prompt execution, browser support, and parallel-agent workflows. See `references/commands/command--agents.md`.
- `utils`: machine, project, and file utilities. See `references/commands/command--utils.md`.
- `seek`: interactive search across files, text, and symbols. See `references/commands/command--seek.md`.
- `fire`: run Python files and functions as jobs. See `references/commands/command--fire.md`.
- `preview`: preview local files or generated artifacts. See `references/commands/command--preview.md`.

## Reference Files

- `references/cli-map.md`: top-level entrypoint and command-reference index.
- `references/source-map.md`: root entrypoint source index.
- `references/commands/*.md`: one-level command pages; each page links to the next command level.

## Practical Rules

- Prefer these for repo-local reproducibility:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```
- Use long flags in guidance.
- Do not rely on aliases in examples unless the user explicitly asks about aliases.
- After changing command behavior, run the narrow command help path and any focused tests or type checks for touched Python files.
