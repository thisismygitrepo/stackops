import os
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_agents.agents_local.constants import (
    LOCAL_DEFAULT_BACKEND,
    OLLAMA_CATALOG_TIMEOUT_SECONDS,
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DISCOVER_LIMIT,
    OLLAMA_DISCOVER_MAX_PARAMS,
    OLLAMA_DISCOVER_MIN_PARAMS,
    OLLAMA_DISCOVER_SORT,
    OLLAMA_TIMEOUT_SECONDS,
    VLLM_DEFAULT_HOST,
    VLLM_DISCOVER_SORT,
    VLLM_TIMEOUT_SECONDS,
    CatalogCapability,
    CatalogSort,
    LocalBackend,
)


def doctor(
    backend: Annotated[
        LocalBackend, typer.Option("--backend", "-b", help="Local model server to inspect."),
    ] = LOCAL_DEFAULT_BACKEND,
    host: Annotated[
        str | None,
        typer.Option("--host", "-H", help="Server address. Defaults to OLLAMA_HOST or VLLM_BASE_URL, then the backend's local address."),
    ] = None,
    timeout: Annotated[
        float | None,
        typer.Option("--timeout", "-t", min=0.1, help="Timeout in seconds for each API request (default: 5)."),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option("--api-key", "-k", envvar="VLLM_API_KEY", show_envvar=True, help="vLLM bearer token."),
    ] = None,
) -> None:
    try:
        if backend == "vllm":
            from stackops.scripts.python.helpers.helpers_agents.agents_local.vllm import collect_vllm_status
            from stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_report import show_vllm_doctor

            vllm_status = collect_vllm_status(
                host=host if host is not None else os.environ.get("VLLM_BASE_URL", VLLM_DEFAULT_HOST),
                timeout=timeout if timeout is not None else VLLM_TIMEOUT_SECONDS,
                api_key=api_key,
            )
            show_vllm_doctor(status=vllm_status)
            errors = vllm_status.errors
        else:
            from stackops.scripts.python.helpers.helpers_agents.agents_local.ollama import collect_ollama_status
            from stackops.scripts.python.helpers.helpers_agents.agents_local.report import show_local_doctor

            status = collect_ollama_status(
                host=host if host is not None else os.environ.get("OLLAMA_HOST", OLLAMA_DEFAULT_HOST),
                timeout=timeout if timeout is not None else OLLAMA_TIMEOUT_SECONDS,
            )
            show_local_doctor(status=status)
            errors = status.errors
    except ValueError as error:
        raise typer.BadParameter(str(error), param_hint="--host") from error

    if errors:
        raise typer.Exit(code=1)


def discover(
    query: Annotated[str, typer.Argument(help="Filter model names (and descriptions for Ollama).")] = "",
    backend: Annotated[
        LocalBackend, typer.Option("--backend", "-b", help="Model catalog: Ollama or Hugging Face models for vLLM."),
    ] = LOCAL_DEFAULT_BACKEND,
    min_params: Annotated[
        float, typer.Option("--min-params", "-l", min=0.0, help="Minimum advertised parameter count, in billions (inclusive)."),
    ] = OLLAMA_DISCOVER_MIN_PARAMS,
    max_params: Annotated[
        float, typer.Option("--max-params", "-m", min=0.001, help="Maximum advertised parameter count, in billions."),
    ] = OLLAMA_DISCOVER_MAX_PARAMS,
    sort: Annotated[
        CatalogSort | None,
        typer.Option("--sort", "-s", help="Catalog ordering; not a quality ranking. Ollama: newest|popular (default newest). vLLM: popular|trending (default popular)."),
    ] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1, help="Maximum number of models or Ollama model families to show.")] = OLLAMA_DISCOVER_LIMIT,
    capability: Annotated[
        CatalogCapability | None, typer.Option("--capability", "-c", help="Ollama only: require a capability advertised by the model family."),
    ] = None,
    timeout: Annotated[
        float, typer.Option("--timeout", "-t", min=0.1, help="Timeout in seconds for each catalog or download-size request."),
    ] = OLLAMA_CATALOG_TIMEOUT_SECONDS,
) -> None:
    if min_params > max_params:
        raise typer.BadParameter("Must be less than or equal to --max-params.", param_hint="--min-params")
    if backend == "vllm" and capability is not None:
        raise typer.BadParameter("Capability filtering is only available for the Ollama catalog.", param_hint="--capability")
    resolved_sort: CatalogSort = sort or (VLLM_DISCOVER_SORT if backend == "vllm" else OLLAMA_DISCOVER_SORT)

    import requests
    from rich.console import Console
    from rich.text import Text

    catalog_name = "Hugging Face vLLM" if backend == "vllm" else "Ollama"
    try:
        if backend == "vllm":
            from stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog import discover_vllm_models
            from stackops.scripts.python.helpers.helpers_agents.agents_local.vllm_catalog_report import show_discovered_vllm_models

            with Console().status("Fetching current Hugging Face models for vLLM..."):
                vllm_models = discover_vllm_models(
                    min_params=min_params, max_params=max_params, sort=resolved_sort, limit=limit, query=query, capability=capability, timeout=timeout,
                )
            show_discovered_vllm_models(models=vllm_models, min_params=min_params, max_params=max_params, sort=resolved_sort)
        else:
            from stackops.scripts.python.helpers.helpers_agents.agents_local.catalog import discover_models
            from stackops.scripts.python.helpers.helpers_agents.agents_local.catalog_report import show_discovered_models

            with Console().status("Fetching current Ollama catalog and download sizes..."):
                models = discover_models(
                    min_params=min_params, max_params=max_params, sort=resolved_sort, limit=limit, query=query, capability=capability, timeout=timeout,
                )
            show_discovered_models(models=models, min_params=min_params, max_params=max_params, sort=resolved_sort)
    except (requests.RequestException, ValueError) as error:
        Console(stderr=True).print(Text(f"""Could not discover {catalog_name} models: {error}""", style="red"))
        raise typer.Exit(code=1) from error


def get_app() -> typer.Typer:
    from stackops.scripts.python.agents_local_vllm import install, serve

    local_app = typer.Typer(
        help="Local models through Ollama and vLLM", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    local_app.command(name="doctor", no_args_is_help=False, short_help="🩺 <d> Inspect server health, models, and resource usage")(doctor)
    local_app.command(name="d", no_args_is_help=False, hidden=True)(doctor)
    local_app.command(name="discover", no_args_is_help=False, short_help="🔎 <s> Discover models from Ollama or Hugging Face for vLLM")(discover)
    local_app.command(name="s", no_args_is_help=False, hidden=True)(discover)
    local_app.command(
        name="install", no_args_is_help=False,
        help="Install vLLM for Linux CUDA using uv, or vLLM Metal for Apple Silicon using Homebrew.",
        short_help="📦 <i> Install vLLM for Linux CUDA or Apple Silicon",
    )(install)
    local_app.command(name="i", no_args_is_help=False, hidden=True)(install)
    serve_context_settings = {"allow_extra_args": True, "ignore_unknown_options": True}
    local_app.command(
        name="serve", no_args_is_help=True, short_help="🚀 <S> Start a vLLM model server in the foreground", context_settings=serve_context_settings,
    )(serve)
    local_app.command(name="S", no_args_is_help=True, hidden=True, context_settings=serve_context_settings)(serve)
    return local_app
