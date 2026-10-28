from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.managed_agent_files import AgentManagedFileKind, AgentManagedFileSource, resolve_agent_managed_file_path
from stackops.utils.managed_file_cli import run_managed_file_action


def config_path(
    kind: Annotated[AgentManagedFileKind, typer.Argument(help="Agent configuration file kind.")],
    source: Annotated[AgentManagedFileSource, typer.Option("--source", "-s", help="Configuration source to locate.")] = "workspace",
    custom_path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Explicit configuration file instead of --source.")] = None,
) -> None:
    try:
        resolved_path = custom_path if custom_path is not None else resolve_agent_managed_file_path(kind=kind, source=source)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    run_managed_file_action(kind=kind, action="path", path=resolved_path)


def config_init(
    kind: Annotated[AgentManagedFileKind, typer.Argument(help="Agent configuration file kind.")],
    source: Annotated[AgentManagedFileSource, typer.Option("--source", "-s", help="Configuration source to initialize.")] = "workspace",
    custom_path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Explicit configuration file instead of --source.")] = None,
) -> None:
    try:
        resolved_path = custom_path if custom_path is not None else resolve_agent_managed_file_path(kind=kind, source=source)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    run_managed_file_action(kind=kind, action="init", path=resolved_path)


def config_validate(
    kind: Annotated[AgentManagedFileKind, typer.Argument(help="Agent configuration file kind.")],
    source: Annotated[AgentManagedFileSource, typer.Option("--source", "-s", help="Configuration source to validate.")] = "workspace",
    custom_path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Explicit configuration file instead of --source.")] = None,
) -> None:
    try:
        resolved_path = custom_path if custom_path is not None else resolve_agent_managed_file_path(kind=kind, source=source)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    run_managed_file_action(kind=kind, action="validate", path=resolved_path)


def get_app() -> typer.Typer:
    app = typer.Typer(
        no_args_is_help=True,
        add_completion=False,
        help="Locate, initialize, and validate StackOps prompts, parallel workflow, and MCP catalogs.",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    app.command("path", help="📍 <p> Print the configuration and schema paths as JSON.")(config_path)
    app.command("p", hidden=True)(config_path)
    app.command("init", help="📄 <i> Create missing configuration and schema files.")(config_init)
    app.command("i", hidden=True)(config_init)
    app.command("validate", help="🔍 <v> Check configuration schema and values without launching an agent.")(config_validate)
    app.command("v", hidden=True)(config_validate)
    return app
