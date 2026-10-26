---
name: build-typer-cli
description: >
  Use when the task changes a Typer command surface: adding, renaming, editing, or removing a
  Typer command, option, or hidden one-letter alias; restructuring a Typer app's routers or
  lazy proxies; or fixing slow startup or heavy imports during Typer command discovery.
  NEVER for argparse, click-only, or other non-Typer CLIs, for running or explaining an
  existing command, for changing what a callback does while its registration and signature
  stay the same, or for general performance or import work outside CLI command discovery.
---

# Build Typer CLI

Keep command discovery limited to Typer, standard-library modules, and lightweight CLI contracts. Import implementation modules only after the user selects the command that needs them.

## Add, Edit, or Remove Commands and Options

1. Trace the real invocation through the console entrypoint, parent `get_app()` registrations, any lazy proxy, the selected callback, and its implementation. Use current `--help` and source to identify the owning files.
2. For additions, register the command in its owning router and implement the selected callback. Define arguments and options in that callback's signature. Add a hidden alias only when requested or established by the surrounding command group, using the same callback or proxy and routing flags.
3. For edits, change the owning callback signature or implementation and the affected registrations/help together. Preserve behavior outside the requested change; an explicitly requested rename or parsing change replaces that part of the old contract.
4. For command removals, remove the canonical registration and its aliases together. Remove a callback, proxy, import, or implementation only after checking its other callers. For an option removal, keep the command registered and remove the option definition and its value handling in the callback and implementation.
5. Verify the affected help path or an existing focused behavior check under the repository's validation rules. Report the command path and changed files. Do not add tests, run profiling, or expand into unrelated routing refactors for a routine change.

Read [references/lazy-routing-patterns.md](references/lazy-routing-patterns.md) when the change involves proxies, nested groups, or aliases. Use the workflow below for creating or restructuring a CLI or investigating startup performance.

## CLI Design and Performance Workflow

1. Trace the real invocation.

- Resolve shell wrappers, console-script entrypoints, root `main()`, `get_app()`, nested apps, and the selected callback.
- Search registrations and imports before editing. Do not optimize an assumed entrypoint.
- Preserve existing user changes when the worktree is dirty.

2. Establish a baseline or acceptance target.

- For performance work on an existing CLI, measure the exact user command with `hyperfine`.
- For a new CLI, identify root, group, and representative leaf help paths plus the modules each path may import.
- For performance work, record peak RSS with `/usr/bin/time`, rank cumulative imports with `PYTHONPROFILEIMPORTTIME=1`, and measure root help and representative leaf help separately.

Read [references/measurement-and-validation.md](references/measurement-and-validation.md) for commands and regression tests.

3. Classify every startup import.

- Keep module-level imports only when Typer needs the object to construct the current help surface.
- Move runtime-only imports into the selected callback or the helper that first uses them.
- Keep callback annotation types and default constants in lightweight contract or constants modules.
- Treat package `__init__.py` files as empty; do not use export shims.

4. Select the smallest lazy boundary.

- Use body-local imports for isolated heavy dependencies.
- Use a lightweight router when a group contains several independent heavy commands.
- Use a proxy command to defer an entire nested Typer app.
- Prefer direct console entrypoints for frequently used large command families; keep umbrella dispatchers lightweight.

Read [references/lazy-routing-patterns.md](references/lazy-routing-patterns.md) before implementing nested groups, leaf proxies, or one-letter command shorts.

5. Add discoverable one-letter command shorts when useful.

- Treat `<d>` as a help marker only. It does not create the `d` command.
- Choose a unique, case-sensitive short within the sibling command scope. Register the canonical name first and the hidden short against the exact same callback or lazy proxy.
- Keep parsing and routing flags identical between both registrations, including `context_settings`, `no_args_is_help`, and `add_help_option`.
- Use the repository's established marker helper when one exists. Ensure it derives markers from real hidden aliases instead of maintaining an unrelated help-only convention.

6. Preserve the CLI contract.

- Preserve canonical names, hidden aliases, option parsing, required arguments, help text, exit behavior, and whether no arguments show help or execute, except where the user explicitly requests a change to that contract.
- Forward `ctx.args` explicitly and pass `--help` only for commands whose no-argument behavior is help.
- Set `standalone_mode=False` for nested invocation so the outer application owns process exit behavior.
- Pass `prog_name=ctx.command_path` so nested usage text shows the selected path.

7. Validate proportionally.

- Run root, canonical child, hidden alias, and representative leaf help paths.
- Confirm root help shows each short marker once beside its canonical command and does not show the hidden alias as a separate row.
- Follow the repository's validation rules and use existing focused checks for the affected behavior. Add import-regression or routing tests only when test work is requested.
- For performance work, re-run the same benchmark and report time and RSS before versus after.

## Non-Negotiable Rules

- Do not import every child callback inside `get_app()`.
- Do not use string-based `importlib` dispatch when explicit local imports preserve static rename checking.
- Do not hide callback-signature types behind `TYPE_CHECKING`; Typer resolves those annotations at runtime.
- Do not duplicate heavy default values in a router. Move shared defaults to a lightweight constants module.
- Do not mistake an angle-bracket help marker for a registered command short.
- Do not implement a separate wrapper for a short. Bind the canonical name and hidden short to the same callback or proxy so routing and marker derivation cannot drift.
- Do not build compatibility routers alongside old eager routers. Keep one strict registration path.
- Do not execute real jobs, network calls, browser actions, or database work while benchmarking; use help paths.
- For performance work, do not claim success from wall time alone; consider imports, RSS, and behavior within the permitted validation scope.

## Completion Criteria

Finish when the requested command or option behavior is implemented, unaffected CLI behavior remains intact, affected aliases stay consistent, and the permitted focused check passes. For CLI design or restructuring, also verify the intended lazy import boundaries. For performance work, require measured startup to materially improve or demonstrate that the remaining cost is framework or runner overhead.
