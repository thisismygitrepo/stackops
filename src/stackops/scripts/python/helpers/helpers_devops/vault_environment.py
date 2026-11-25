import os
import shlex
import subprocess
from collections.abc import Mapping
from typing import NoReturn

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.secrets.search import render_secret_value


def parse_load_command(command: str | None) -> list[str] | None:
    try:
        command_args = shlex.split(command) if command is not None else None
    except ValueError as error:
        raise typer.BadParameter("--command contains invalid argument quoting.") from error
    if command_args == []:
        raise typer.BadParameter("--command must contain an executable.")
    if command_args is None and not os.environ.get("OP_PROGRAM_PATH"):
        raise typer.BadParameter("Use --command 'PROGRAM ARGUMENTS' to run with secrets, or invoke load through the StackOps shell wrapper.")
    return command_args


def run_command_with_environment(command_args: list[str], key_values: Mapping[str, object]) -> NoReturn:
    secret_actions.validate_env_names(key_values)
    environment = os.environ.copy()
    environment.update({key: render_secret_value(value) for key, value in key_values.items()})
    try:
        result = subprocess.run(command_args, env=environment, check=False)
    except OSError as error:
        typer.echo(f"Could not start child command: {error.strerror}", err=True)
        raise typer.Exit(code=1) from error
    raise typer.Exit(code=result.returncode if result.returncode >= 0 else 128 - result.returncode)


def prepare_shell_environment(key_values: Mapping[str, object], *, origin: str | None, verbose: bool) -> None:
    secret_actions.validate_env_names(key_values)
    secret_actions.write_env_handoff(key_values, verbose=verbose)
    variable_noun = "variable" if len(key_values) == 1 else "variables"
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(key_values)} environment {variable_noun}"
    if origin is not None:
        msg += f" from {origin}"
    typer.echo(f"{msg}: {', '.join(key_values)}.")
