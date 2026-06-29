# Lazy Routing Patterns

## Contents

1. Import budget
2. Body-local imports
3. Lazy nested apps
4. Lazy leaf callbacks
5. One-letter command shorts
6. Registration rules
7. Runtime typing constraints
8. Architecture choices

## 1. Import Budget

A help path should load only:

- the console-script module;
- Typer and its required UI dependencies;
- the routers needed to display the current command level;
- standard-library modules;
- lightweight `Literal`, enum, option metadata, and default constants needed for the current callback signature.

It should not load database drivers, exchange clients, HTTP stacks, plotting libraries, dataframe engines, numerical libraries, ML frameworks, cloud SDKs, configuration backends, or job implementations.

Remember that Typer inspects callback signatures to construct Click commands. A heavy import used only to provide an annotation or default is still an eager dependency.

## 2. Body-Local Imports

Start with the narrowest change:

```python
from typing import Annotated

import typer

from project.cli.contracts import ExchangeName


def stream(
    exchange: Annotated[ExchangeName, typer.Option("--exchange")],
) -> None:
    from project.streaming.runtime import run_stream

    run_stream(exchange=exchange)
```

Keep `ExchangeName` lightweight. Move runtime dependencies into `run_stream()` or the callback body.

When a default currently lives in a heavy implementation module, move it to a lightweight `constants.py` and import it from both the CLI callback and implementation. Do not copy the value.

## 3. Lazy Nested Apps

Use Typer's normal composition when every child router is lightweight:

```python
import typer

from project.cli.reports_router import get_app as get_reports_app


def get_app() -> typer.Typer:
    app = typer.Typer(add_completion=False, no_args_is_help=True)
    app.add_typer(
        get_reports_app(),
        name="reports",
        help="Generate and inspect reports",
    )
    return app
```

This preserves Typer's native nested help and completion behavior. It still imports and constructs the child router whenever the parent app is built, so keep that child router free of implementation imports.

Use a proxy callback when the parent must list a group without importing even the child router:

```python
import typer


PROXY_CONTEXT_SETTINGS = {
    "allow_extra_args": True,
    "ignore_unknown_options": True,
    "help_option_names": [],
}


def reports(ctx: typer.Context) -> None:
    from project.cli.reports import get_app as get_reports_app

    arguments = ctx.args or ["--help"]
    get_reports_app()(
        arguments,
        prog_name=ctx.command_path,
        standalone_mode=False,
    )


def get_app() -> typer.Typer:
    app = typer.Typer(add_completion=False, no_args_is_help=True)
    app.command(
        "reports",
        help="Generate and inspect reports",
        context_settings=PROXY_CONTEXT_SETTINGS,
        no_args_is_help=False,
        add_help_option=False,
    )(reports)
    return app
```

The outer proxy uses `no_args_is_help=False` because the callback must run to import the child and render child help. Disable the proxy's help option so `--help` reaches the child.

Use `app.add_typer(child_app)` when importing and constructing `child_app` is demonstrably lightweight. It is not lazy merely because the callback implementations use local imports.

Keep `@app.callback()` functions lightweight because they run for every selected child command. Parse global flags there, but defer configuration loading, clients, and service initialization until the leaf that needs them.

## 4. Lazy Leaf Callbacks

When a router must expose static leaf names without importing callback signatures, register context-only proxies and create a one-command Typer app after selection:

```python
from collections.abc import Callable

import typer


type CommandCallback = Callable[..., object]


def invoke_command(
    ctx: typer.Context,
    command: CommandCallback,
    no_args_is_help: bool,
) -> None:
    app = typer.Typer(
        add_completion=False,
        no_args_is_help=no_args_is_help,
    )
    app.command()(command)
    arguments = ctx.args if ctx.args or not no_args_is_help else ["--help"]
    app(
        arguments,
        prog_name=ctx.command_path,
        standalone_mode=False,
    )


def stream_proxy(ctx: typer.Context) -> None:
    from project.cli.stream import stream

    invoke_command(ctx=ctx, command=stream, no_args_is_help=True)


def browser_proxy(ctx: typer.Context) -> None:
    from project.cli.browser import open_browser

    invoke_command(ctx=ctx, command=open_browser, no_args_is_help=False)
```

This preserves the distinction between commands that show help with no arguments and commands that execute with defaults.

Register each proxy with:

```python
app.command(
    "stream",
    help="Start a live stream",
    context_settings=PROXY_CONTEXT_SETTINGS,
    no_args_is_help=False,
    add_help_option=False,
)(stream_proxy)
```

Add one-letter command shorts as described in the next section. Both names must use the same proxy callback.

## 5. One-Letter Command Shorts

A one-letter command short is a real hidden sibling command. It is not a dashed option, and an angle-bracket marker such as `<d>` in help text does not create it.

Register the canonical name and short next to each other against the exact same callback:

```python
app.command(
    "data",
    help="<d> Data management",
    context_settings=PROXY_CONTEXT_SETTINGS,
    no_args_is_help=False,
    add_help_option=False,
)(data_proxy)
app.command(
    "d",
    hidden=True,
    context_settings=PROXY_CONTEXT_SETTINGS,
    no_args_is_help=False,
    add_help_option=False,
)(data_proxy)
```

The visible row advertises `<d>`, while the hidden registration makes `my-cli d` executable. Keep `context_settings`, `no_args_is_help`, `add_help_option`, and every other routing flag identical. Sharing the proxy preserves its local-import boundary for both names.

For an eagerly composed lightweight group, register the same child app under both names:

```python
data_app = get_data_app()
app.add_typer(data_app, name="data", help="<d> Data management")
app.add_typer(data_app, name="d", hidden=True)
```

Do not build the child eagerly merely to add a short. When the child must remain lazy, use the paired proxy-command pattern instead.

Choose a unique, case-sensitive one-character short within each sibling scope. Lowercase and uppercase names are different commands. Keep canonical names in documentation and primary behavior tests; test each short separately.

If the repository provides an alias-marker helper, use its established contract. A StackOps-style `apply_alias_markers(app)` derives markers from hidden one-character registrations that share callback identity, updates explicit `help` or `short_help`, and recurses through eagerly composed child apps. Return the processed app from every router, and process a lazily built child after importing it. Still register the hidden command: marker injection is presentation, not routing.

Inspect helper constraints before relying on automatic markers. In particular, preserve callback identity, provide explicit help text when required, register canonical and hidden `add_typer` entries adjacently when pairing is order-based, and reject alias collisions instead of selecting a fallback.

Validate all of these properties:

- Root help contains the canonical row with exactly one matching marker and no separate alias row.
- Canonical and short help both succeed and preserve arguments, options, no-argument behavior, exit codes, and the selected `ctx.command_path`.
- Root help imports neither the lazy child nor its leaves; short-selected help imports only the selected lightweight router or contract.

Use explicit local imports per proxy. They let type checkers and repository-wide rename tools find every implementation edge.

## 6. Registration Rules

- Keep parent-level help strings in the lightweight router because help must render before the leaf import.
- Centralize shared command metadata in a lightweight contract module when more than one router consumes it.
- Keep one `get_app()` registration path. If an implementation module previously exposed `get_app()`, make it delegate to the lazy router or remove it and update all callers.
- Construct the app inside `get_app()` or `main()`. Avoid package-import side effects and global app exports from `__init__.py`.
- Use canonical commands in documentation and tests. Test aliases separately but keep them hidden.
- Use direct entrypoints for large independent command families so common commands avoid umbrella routing overhead.

## 7. Runtime Typing Constraints

Typer resolves annotations when it builds the selected Click command.

- Keep every type used in a callback signature available at runtime.
- Do not place callback signature imports exclusively under `TYPE_CHECKING`.
- Prefer lightweight `Literal`, `TypeAlias`, enum, `TypedDict`, or dataclass contract modules.
- Put helper-only annotations behind `TYPE_CHECKING` when the runtime helper does not inspect them.
- Avoid `Any` and string module paths for dispatch. Use `Callable[..., object]` only at the generic Typer callback boundary.

Python 3.14 lazy annotations delay evaluation, but Typer's runtime inspection still evaluates selected callback annotations. Lazy language semantics do not remove this constraint.

## 8. Architecture Choices

Use this order:

1. Move runtime-only imports into callback bodies.
2. Split heavyweight implementations from lightweight callback contracts.
3. Add a lazy group or leaf proxy where parent discovery still imports children.
4. Add direct console entrypoints for large command families.
5. Consider a custom Click `Group` only for plugin systems or very large dynamic command sets.

A custom lazy `Group` can override command listing and resolution, but it increases Click/Typer version coupling and often requires string-based module maps. Prefer explicit typed proxies for normal application CLIs.
