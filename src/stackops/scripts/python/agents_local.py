from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import (
    OLLAMA_CATALOG_TIMEOUT_SECONDS,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DISCOVER_LIMIT,
    OLLAMA_DISCOVER_MAX_PARAMS,
    OLLAMA_DISCOVER_MIN_PARAMS,
    OLLAMA_DISCOVER_SORT,
    OLLAMA_TIMEOUT_SECONDS,
    CatalogCapability,
    CatalogSort,
)


def doctor(
    host: Annotated[
        str,
        typer.Option("--host", "-H", envvar="OLLAMA_HOST", help="Ollama server address."),
    ] = OLLAMA_DEFAULT_HOST,
    timeout: Annotated[
        float,
        typer.Option("--timeout", "-t", min=0.1, help="Timeout in seconds for each Ollama API request."),
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


def discover(
    query: Annotated[str, typer.Argument(help="Filter model names and descriptions.")] = "",
    min_params: Annotated[
        float, typer.Option("--min-params", "-l", min=0.0, help="Minimum advertised parameter count, in billions (inclusive)."),
    ] = OLLAMA_DISCOVER_MIN_PARAMS,
    max_params: Annotated[
        float, typer.Option("--max-params", "-m", min=0.001, help="Maximum advertised parameter count, in billions."),
    ] = OLLAMA_DISCOVER_MAX_PARAMS,
    sort: Annotated[CatalogSort, typer.Option("--sort", "-s", help="Ollama catalog ordering; not a quality ranking.")] = OLLAMA_DISCOVER_SORT,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum number of model families to show.")] = OLLAMA_DISCOVER_LIMIT,
    capability: Annotated[
        CatalogCapability | None, typer.Option("--capability", "-c", help="Require a capability advertised by the model family."),
    ] = None,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", min=0.1, help="Timeout in seconds for each catalog or download-size request."),
    ] = OLLAMA_CATALOG_TIMEOUT_SECONDS,
) -> None:
    import requests
    from rich.console import Console
    from rich.text import Text

    from stackops.scripts.python.helpers.helpers_agents.agents_local.catalog import discover_models
    from stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_report import show_discovered_models

    if min_params > max_params:
        raise typer.BadParameter("Must be less than or equal to --max-params.", param_hint="--min-params")

    try:
        with Console().status("Fetching current Ollama catalog and download sizes..."):
            models = discover_models(
                min_params=min_params, max_params=max_params, sort=sort, limit=limit, query=query, capability=capability, timeout=timeout,
            )
    except (requests.RequestException, ValueError) as error:
        Console(stderr=True).print(Text(f"""Could not discover Ollama models: {error}""", style="red"))
        raise typer.Exit(code=1) from error
    show_discovered_models(models=models, min_params=min_params, max_params=max_params, sort=sort)


def get_app() -> typer.Typer:
    local_app = typer.Typer(
        help="Local models through Ollama", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    local_app.command(name="doctor", no_args_is_help=False, short_help="🩺 <d> Inspect Ollama health, models, and resource usage")(doctor)
    local_app.command(name="d", no_args_is_help=False, hidden=True)(doctor)
    local_app.command(name="discover", no_args_is_help=False, short_help="Discover current Ollama models by size and capability")(discover)
    local_app.command(name="s", no_args_is_help=False, hidden=True)(discover)
    return local_app
