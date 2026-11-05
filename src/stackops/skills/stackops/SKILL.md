---
name: stackops
description: >
  Use ONLY when the user explicitly names stackops (e.g. "use stackops to add a layout
  entry") or invokes /skill:stackops; then it finds and changes the StackOps command,
  configuration file, schema, or Python implementation that owns the behavior through live
  help and source maps. NEVER for generic CLI, config, layout, settings, catalog, or agent
  work that does not name stackops, for working inside the StackOps repo without naming it,
  or for an entrypoint word alone (devops, cloud, terminal, agents, utils, fire, preview, seek).
---

# StackOps

Use this skill to run StackOps, or to move from a StackOps request to the command, configuration file, or implementation that owns the requested behavior.

## Usage

Commands below use installed entrypoints. Run them from the target project, because local configuration can depend on the current directory. Find anything else with `<entrypoint> --help`, repeating for each command segment.

### Run without prompts

In a terminal, a command with missing input opens a picker or editor and waits for a person. Prevent that on every run:

```bash
STACKOPS_NON_INTERACTIVE=1 agents add-skill --list --json </dev/null
```

- `STACKOPS_NON_INTERACTIVE=1` makes a command exit with an error naming the input it needs, instead of opening a picker or editor.
- `</dev/null` ends direct prompts that do not check that setting.
- This mode turns on by itself when stdin or stdout is not a terminal. Set it anyway, because a shell tool may run under a pseudo-terminal.
- `--non-interactive` is the option form. It goes on the entrypoint, before the subcommand: `agents --non-interactive add-skill`. `seek`, `preview`, and `agents run-prompt` also accept it directly.
- Do not use `-N` after a subcommand, where it can mean something else: `--sandbox-name` on `agents run-prompt`, `--secret-name` on `devops vault search`.

### Tasks

Read-only:

| I want to | Run |
| --- | --- |
| Search text | `seek PATH TERM --json` |
| Show a file | `preview PATH --backend preview` |
| Find installable software | `devops software list QUERY --json` |
| List saved layouts | `terminal list --tabs --json` |
| See running sessions | `terminal summary --json` |
| List registered repositories | `devops repos list --json` |
| See agents and their state | `agents status --json` |
| Check an agent's setup | `agents doctor AGENT --json` |
| List installable skills | `agents add-skill --list --json` |

Changes the machine or remote data, so run these only when asked:

| I want to | Run |
| --- | --- |
| Install software | `devops software install NAME` |
| Launch a saved layout | `terminal run --choose-layouts NAME` |
| Run a Python file | `fire run PATH` |
| Call a Python function | `fire run PATH FUNCTION`, from a project environment that has the `fire` package |
| Copy to or from cloud storage | `cloud copy SOURCE TARGET` |
| Sync with cloud storage | `cloud sync SOURCE TARGET` |
| Copy between machines over SSH | `cloud transfer MACHINE:PATH MACHINE:PATH` |
| Back up or restore registered data | `devops data sync up` or `devops data sync down` |
| Run a command in every repository | `devops repos action --command "COMMAND"` |
| Set up an agent in this repository | `agents init AGENT` |
| Add a skill | `agents add-skill NAME` |
| Add an MCP server | `agents add-mcp NAME --agent AGENT` |
| Ask an agent a question | `agents ask --agent AGENT "QUESTION"` |

## Changing StackOps

For add, edit, rename, or remove requests, read `references/change-guide.md`. It covers choosing configuration versus code, locating the active source, making the change, and validating it, including a layout walkthrough.

Run configuration discovery from the user's target project: local paths can depend on the current directory or repository. Resolve a StackOps source checkout only when inspecting or changing its implementation; verify it contains `pyproject.toml` and `src/stackops/` instead of assuming a workspace location. Resolve `src/stackops/...` paths and run source maintenance commands from that checkout. Paths under `references/` are relative to the directory containing this `SKILL.md`. The Usage section needs none of them.

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

- `references/change-guide.md`: add, edit, rename, or remove configuration entries and command behavior.
- `references/cli-map.md`: top-level entrypoint index.
- `references/source-map.md`: source index of umbrella dispatch routes.

## Practical Rules

- Prefer these for repo-local reproducibility:
```bash
UV_CACHE_DIR=/tmp/uv-cache uv run devops --help
```
- Use long flags in guidance.
- Validate the changed file with its existing validator, or choose a focused check for changed code. Follow repository instructions on tests and tooling; ordinary configuration edits do not require code, schema, or generated-reference changes.
