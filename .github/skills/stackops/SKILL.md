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

2. Resolve command path before acting.
- Start with `<command> --help`.
- Drill down with `<command> <subcommand> --help` until you hit a leaf command.
- Use canonical command names only (no short aliases).
- Prefer the shortest direct entrypoint that reaches the command.

3. Use references only when they reduce search.
- Load `references/cli-map.md` to inspect the command tree, available direct entrypoints, nested subcommands, and CLI nuances.
- Load `references/source-map.md` to jump from a command path to the Typer registration file or leaf implementation.
- Inspect `src/stackops/scripts/python/graph/cli_graph.json` only when aliases, full node metadata, or generated-map debugging matter.

4. Follow source, not old docs.
- Treat Typer registrations in source as the source of truth.
- If docs conflict with source, explain the mismatch and proceed with the source-backed command.

5. Map command to implementation.
- Use `references/source-map.md` to jump directly to the file that registers or implements the command.
- Remember `stackops_entry.py` is a lazy dispatcher; most behavior lives in helper modules.
- When adding or changing commands, update the Typer registration and the helper implementation together, then re-check `--help`.

6. Refresh generated references after CLI shape changes.
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets update-skill-refs
```

7. Run safely.
- Commands under install/update/network/config may mutate system state.
- Call out side effects and require explicit confirmation for risky actions.

## Command Surface

Highlights:
- Primary commands: `devops`, `cloud`, `terminal`, `agents`, `utils`, `fire`, `preview`, `seek`, and umbrella `stackops`.
- This skill intentionally excludes command aliases.
- `devops self docs`, `devops self build-docker`, `devops self build-assets`, and `devops self agentops` appear only when `~/code/stackops` exists.

## Practical Rules

- Prefer these for repo-local reproducibility:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
UV_CACHE_DIR=/tmp/uv-cache uv run devops repos --help
```
- Use long flags in guidance.
- Do not rely on aliases in examples unless the user explicitly asks about aliases.
- After changing command behavior, run the narrow command help path and any focused tests or type checks for touched Python files.
