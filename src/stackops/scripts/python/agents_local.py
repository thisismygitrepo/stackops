from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import OLLAMA_DEFAULT_HOST, OLLAMA_TIMEOUT_SECONDS


def doctor(
    host: Annotated[
        str,
        typer.Option("--host", envvar="OLLAMA_HOST", help="Ollama server address."),
    ] = OLLAMA_DEFAULT_HOST,
    timeout: Annotated[
        float,
        typer.Option("--timeout", min=0.1, help="Timeout in seconds for each Ollama API request."),
    ] = OLLAMA_TIMEOUT_SECONDS,
) -> None:
    from stackops.scripts.python.helpers.helpers_agents.agents_local.ollama import collect_ollama_status
    from stackops.scripts.python.helpers.helpers_agents.agents_local.report import show_local_doctor

    try:
        status = collect_ollama_status(host=host, timeout=timeout)
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--host") from error

    show_local_doctor(status=status)
    if status.errors:
        raise typer.Exit(code=1)


def get_app() -> typer.Typer:
    local_app = typer.Typer(help="Local models through Ollama", no_args_is_help=True, add_help_option=True, add_completion=False)
    local_app.command(name="doctor", no_args_is_help=False, short_help="<d> Inspect Ollama health, models, and resource usage")(doctor)
    local_app.command(name="d", no_args_is_help=False, hidden=True)(doctor)
    return local_app
