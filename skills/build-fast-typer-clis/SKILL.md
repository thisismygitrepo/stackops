---
name: build-fast-typer-clis
description: Profile, design, refactor, and validate fast Typer CLIs with lazy imports, lightweight routers, nested command groups, aliases, direct entrypoints, and import-regression tests. Use when a Typer command or help screen has slow startup or high memory use; when adding or restructuring nested Typer apps; when heavy database, ML, plotting, cloud, or network dependencies load during command discovery; or when an umbrella CLI must expose many commands without importing every implementation.
---

# Build Fast Typer CLIs

Keep command discovery limited to Typer, standard-library modules, and lightweight CLI contracts. Import implementation modules only after the user selects the command that needs them.

## Workflow

1. Trace the real invocation.

- Resolve shell wrappers, console-script entrypoints, root `main()`, `get_app()`, nested apps, and the selected callback.
- Search registrations and imports before editing. Do not optimize an assumed entrypoint.
- Preserve existing user changes when the worktree is dirty.

2. Establish a baseline.

- Measure the exact user command with `hyperfine`.
- Record peak RSS with `/usr/bin/time`.
- Rank cumulative imports with `PYTHONPROFILEIMPORTTIME=1`.
- Measure root help and representative leaf help separately.

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

Read [references/lazy-routing-patterns.md](references/lazy-routing-patterns.md) before implementing nested groups or leaf proxies.

5. Preserve the CLI contract.

- Preserve canonical names, hidden aliases, option parsing, required arguments, help text, exit behavior, and whether no arguments show help or execute.
- Forward `ctx.args` explicitly and pass `--help` only for commands whose no-argument behavior is help.
- Set `standalone_mode=False` for nested invocation so the outer application owns process exit behavior.
- Pass `prog_name=ctx.command_path` so nested usage text shows the selected path.

6. Validate proportionally.

- Run root, canonical child, hidden alias, and representative leaf help paths.
- Add a fresh-process test asserting root help does not import leaf modules.
- Run focused behavior tests for routing and no-argument semantics.
- Run the repository's formatter/linter and type checker on every touched Python file.
- Re-run the same benchmark and report time and RSS before versus after.

## Non-Negotiable Rules

- Do not import every child callback inside `get_app()`.
- Do not use string-based `importlib` dispatch when explicit local imports preserve static rename checking.
- Do not hide callback-signature types behind `TYPE_CHECKING`; Typer resolves those annotations at runtime.
- Do not duplicate heavy default values in a router. Move shared defaults to a lightweight constants module.
- Do not build compatibility routers alongside old eager routers. Keep one strict registration path.
- Do not execute real jobs, network calls, browser actions, or database work while benchmarking; use help paths.
- Do not claim success from wall time alone. Check imports, RSS, behavior, lint, and types.

## Completion Criteria

Finish only when root help imports no leaf implementation modules, leaf help imports only its own lightweight CLI contract, CLI behavior remains intact, static analysis passes, and measured startup materially improves or the remaining cost is demonstrated to be framework/runner overhead.
