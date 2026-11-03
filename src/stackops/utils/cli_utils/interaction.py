import os
import sys
from functools import partial
from typing import Annotated

import typer
from typer._click.exceptions import UsageError


def is_interactive() -> bool:
    disabled = os.environ.get("STACKOPS_NON_INTERACTIVE", "").casefold() in {"1", "true", "yes"}
    return not disabled and sys.stdin.isatty() and sys.stdout.isatty()


def require_interactive(action: str) -> None:
    if not is_interactive():
        raise UsageError(f"""{action} requires an interactive terminal. Supply explicit inputs or use the command's noninteractive alternative.""")


def _restore_environment(name: str, value: str | None) -> None:
    if value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = value


def configure_interaction(
    ctx: typer.Context,
    non_interactive: Annotated[
        bool,
        typer.Option("--non-interactive", "-N", envvar="STACKOPS_NON_INTERACTIVE", help="Never prompt or open a picker/editor, including in a terminal. Also enabled automatically without a terminal."),
    ] = False,
) -> None:
    if non_interactive or not is_interactive():
        for name, value in {"STACKOPS_NON_INTERACTIVE": "1", "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}.items():
            previous = os.environ.get(name)
            os.environ[name] = value
            ctx.call_on_close(partial(_restore_environment, name, previous))
