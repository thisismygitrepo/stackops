---
name: stackops
description: Teach, execute, troubleshoot, and extend the StackOps CLI/library through live Typer help, direct entrypoints, and source-backed root maps. Use when Codex works with StackOps commands, command discovery, command implementation files, CLI references, or entrypoints such as devops, cloud, terminal, agents, utils, fire, preview, seek, and the stackops umbrella command.
---

# StackOps

Use this skill to move from a StackOps command request to the current Typer surface and implementation files without copying details that the CLI can report itself.

## Quick Workflow

1. Choose the execution form.
- In this repository, run StackOps commands as `UV_CACHE_DIR=/tmp/uv-cache uv run <entrypoint> ...`.
- For installed usage outside the repo, use direct entrypoints: `devops`, `cloud`, `terminal`, `agents`, `utils`, `fire`, `preview`, and `seek`.
- Use `stackops <entrypoint> ...` only when the user specifically wants the umbrella dispatcher or when testing the dispatcher itself.

2. Resolve command path progressively.
- Start with a top-level entrypoint from the list below.
- Run `<entrypoint> --help`, then repeat with each discovered command segment until you reach the needed leaf.
- Do not rely on checked-in text for options, defaults, aliases, or child commands when `--help` can answer.
- Use canonical command names only (no short aliases).
- Prefer the shortest direct entrypoint that reaches the command.

3. Use references only when they reduce search.
- Load `references/cli-map.md` for the top-level CLI index and direct entrypoints.
- Load `references/source-map.md` for the root source index.
- Inspect `src/stackops/scripts/python/graph/cli_graph.json` only when live help and source inspection are insufficient.

4. Follow source, not old docs.
- Treat Typer registrations in source as the source of truth.
- Treat `--help` as the fastest way to discover the current command surface.
- If docs conflict with source or live help, explain the mismatch and proceed with source/live-help behavior.

5. Map command to implementation.
- Use `references/source-map.md` to find the root entrypoint, then inspect Typer registration source for deeper command segments.
- Remember `stackops_entry.py` is a lazy dispatcher; most behavior lives in helper modules after the first command segment.
- When adding or changing commands, update the Typer registration and the helper implementation together, then re-check `--help`.

6. Refresh generated references after CLI shape changes.
- Run `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets update-skill-refs` from the repo root.

7. Run safely.
- Commands that install, update, configure, sync, share, mount, or edit local files may mutate system state.
- Call out side effects and require explicit confirmation for risky actions.

## Top-Level Commands

- `stackops`: umbrella dispatcher and root command index.
- `devops`: developer workstation, project management, machine setup, credentials, connectivity, and StackOps maintenance.
- `cloud`: cloud sync, copy, mount, and transfer workflows.
- `terminal`: terminal session orchestration and summaries.
- `agents`: agent setup, prompt execution, browser support, and parallel-agent workflows.
- `utils`: machine, project, and file utilities.
- `seek`: interactive search across files, text, and symbols.
- `fire`: run Python files and functions as jobs.
- `preview`: preview local files or generated artifacts.

## Reference Files

- `references/cli-map.md`: top-level entrypoint index.
- `references/source-map.md`: root entrypoint source index.

## Practical Rules

- Prefer these for repo-local reproducibility:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```
- Use long flags in guidance.
- Do not rely on aliases in examples unless the user explicitly asks about aliases.
- After changing command behavior, run the narrow command help path and any focused tests or type checks for touched Python files.
