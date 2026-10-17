---
name: stackops
description: Use, troubleshoot, and change StackOps commands and configuration. Use for adding, editing, renaming, or removing layout entries, settings, catalog entries, agent configuration, or CLI behavior; locate the owning file and schema or Python implementation through live help and source maps. Covers devops, cloud, terminal, agents, utils, fire, preview, seek, and the stackops dispatcher.
---

# StackOps

Use this skill to move from a StackOps request to the command, configuration file, or implementation that owns the requested behavior.

For add, edit, rename, or remove requests, read [references/change-guide.md](references/change-guide.md). It covers choosing configuration versus code, locating the active source, making the change, and validating it, including a layout walkthrough.

Run configuration discovery from the user's target project: local paths can depend on the current directory or repository. Resolve a StackOps source checkout only when inspecting or changing its implementation; verify it contains `pyproject.toml` and `src/stackops/` instead of assuming a workspace location. Resolve `src/stackops/...` paths and run source maintenance commands from that checkout. Resolve `references/...` paths from this skill's directory.

## Quick Workflow

1. Choose the execution form.
- In the resolved StackOps checkout, run source maintenance and help commands as `UV_CACHE_DIR=/tmp/uv-cache uv run <entrypoint> ...`.
- For installed usage outside the repo, use direct entrypoints: `devops`, `cloud`, `terminal`, `agents`, `utils`, `fire`, `preview`, and `seek`.
- Keep the target project's working directory for local configuration discovery. When running from the StackOps checkout, pass an explicit target file to avoid selecting the checkout's configuration.
- Use `stackops <entrypoint> ...` only when the user specifically wants the umbrella dispatcher or when testing the dispatcher itself.

2. Resolve command path progressively.
- Start with a top-level entrypoint from the list below.
- Run `<entrypoint> --help`, then repeat with each discovered command segment until you reach the needed leaf.
- Do not rely on checked-in text for options, defaults, or child commands when `--help` can answer.
- Prefer the shortest direct entrypoint that reaches the command.

3. Use references only when they reduce search.
- Load `references/cli-map.md` for the top-level CLI index and direct entrypoints.
- Load `references/source-map.md` for the umbrella dispatch routes. Direct entrypoints start in the modules listed by `references/cli-map.md` and `pyproject.toml` `[project.scripts]`.
- Inspect `src/stackops/scripts/python/graph/cli_graph.json` only when live help and source inspection are insufficient.

4. Follow source, not old docs.
- Treat Typer registrations in source as the source of truth.
- Treat `--help` as the fastest way to discover the current command surface.
- If docs conflict with source or live help, explain the mismatch and proceed with source/live-help behavior.

5. Map the requested change to its owner.
- Saved entries and existing settings usually belong in configuration. Use the change guide's `path` commands and schema before considering a code change.
- For a direct entrypoint, start at its `pyproject.toml` `[project.scripts]` target, indexed in `references/cli-map.md`, then inspect Typer registrations for deeper command segments.
- Use `references/source-map.md` to trace umbrella dispatch. `stackops_entry.py` handles the umbrella command; direct entrypoints start in their own modules, and most behavior lives in helper modules.
- For code changes, trace registration, callback, helper, and any parser/schema together. Update only the layers required by the requested behavior; removal must include the corresponding aliases and callers.

6. Refresh generated references after CLI shape changes.
- Run `UV_CACHE_DIR=/tmp/uv-cache uv run devops self build-assets skill-refs` from the resolved StackOps checkout, then refresh the generated references in installed skill copies.

7. Run safely.
- Commands that install, update, configure, sync, share, mount, or edit local files may mutate system state.
- Keep configuration edits separate from applying them: launching layouts, installing software, syncing data, or starting agents are additional actions. Follow the user's requested scope and existing authorization.

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

- [references/change-guide.md](references/change-guide.md): add, edit, rename, or remove configuration entries and command behavior.
- `references/cli-map.md`: top-level entrypoint index.
- `references/source-map.md`: source index of umbrella dispatch routes.

## Practical Rules

- Prefer these for repo-local reproducibility:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```
- Use long flags in guidance.
- Validate the changed file with its existing validator, or choose a focused check for changed code. Follow repository instructions on tests and tooling; ordinary configuration edits do not require code, schema, or generated-reference changes.
