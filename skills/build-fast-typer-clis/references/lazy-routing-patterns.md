# Lazy Routing Patterns

## Contents

1. Import budget
2. Body-local imports
3. Lazy nested apps
4. Lazy leaf callbacks
5. Registration rules
6. Runtime typing constraints
7. Architecture choices

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

Register a hidden alias against the same proxy:

```python
app.command(
    "s",
    hidden=True,
    context_settings=PROXY_CONTEXT_SETTINGS,
    no_args_is_help=False,
    add_help_option=False,
)(stream_proxy)
```

Use explicit local imports per proxy. They let type checkers and repository-wide rename tools find every implementation edge.

## 5. Registration Rules

- Keep parent-level help strings in the lightweight router because help must render before the leaf import.
- Centralize shared command metadata in a lightweight contract module when more than one router consumes it.
- Keep one `get_app()` registration path. If an implementation module previously exposed `get_app()`, make it delegate to the lazy router or remove it and update all callers.
- Construct the app inside `get_app()` or `main()`. Avoid package-import side effects and global app exports from `__init__.py`.
- Use canonical commands in documentation and tests. Test aliases separately but keep them hidden.
- Use direct entrypoints for large independent command families so common commands avoid umbrella routing overhead.

## 6. Runtime Typing Constraints

Typer resolves annotations when it builds the selected Click command.

- Keep every type used in a callback signature available at runtime.
- Do not place callback signature imports exclusively under `TYPE_CHECKING`.
- Prefer lightweight `Literal`, `TypeAlias`, enum, `TypedDict`, or dataclass contract modules.
- Put helper-only annotations behind `TYPE_CHECKING` when the runtime helper does not inspect them.
- Avoid `Any` and string module paths for dispatch. Use `Callable[..., object]` only at the generic Typer callback boundary.

Python 3.14 lazy annotations delay evaluation, but Typer's runtime inspection still evaluates selected callback annotations. Lazy language semantics do not remove this constraint.

## 7. Architecture Choices

Use this order:

1. Move runtime-only imports into callback bodies.
2. Split heavyweight implementations from lightweight callback contracts.
3. Add a lazy group or leaf proxy where parent discovery still imports children.
4. Add direct console entrypoints for large command families.
5. Consider a custom Click `Group` only for plugin systems or very large dynamic command sets.

A custom lazy `Group` can override command listing and resolution, but it increases Click/Typer version coupling and often requires string-based module maps. Prefer explicit typed proxies for normal application CLIs.
