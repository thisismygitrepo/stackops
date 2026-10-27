import json
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import WritableSecretsSource


def resolve_secrets_file(*, custom_path: Path | None, source: WritableSecretsSource | None) -> Path:
    if custom_path is not None:
        if source in {"user", "u"}:
            raise typer.BadParameter("--custom-path replaces the project secrets source; it cannot be combined with --source user.")
        return custom_path.expanduser().absolute()
    if source is None:
        raise typer.BadParameter("Provide --custom-path or --source project|user. Use devops vault path to see available files.")
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_single_secret_source

    return resolve_single_secret_source(secrets_path=None, secrets_source=source).path


def path_secrets(
    custom_path: Annotated[
        Path | None, typer.Option("--custom-path", "-p", help="Use a custom secrets JSON file in place of the project source."),
    ] = None,
    source: Annotated[
        WritableSecretsSource | None,
        typer.Option("--source", "-s", case_sensitive=False, help="Show project/p or user/u paths. Omit to show all available sources."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    if custom_path is not None or source is not None:
        file_path = resolve_secrets_file(custom_path=custom_path, source=source)
        run_managed_file_action(kind="secrets", action="path", path=file_path)
        return

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_secret_sources
    from stackops.utils.managed_file_operations import describe_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    spec = get_managed_file_spec("secrets")
    paths = {
        secret_source.name: describe_managed_file(spec=spec, data_path=secret_source.path)
        for secret_source in resolve_secret_sources(secrets_path=None, secrets_source="all")
    }
    typer.echo(json.dumps(paths, indent=2))


def init_secrets(
    custom_path: Annotated[
        Path | None, typer.Option("--custom-path", "-p", help="Use a custom secrets JSON file in place of the project source."),
    ] = None,
    source: Annotated[
        WritableSecretsSource | None,
        typer.Option("--source", "-s", case_sensitive=False, help="Secrets file to initialize: project/p or user/u."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_secrets_file(custom_path=custom_path, source=source)
    run_managed_file_action(kind="secrets", action="init", path=file_path)


def validate_secrets(
    custom_path: Annotated[
        Path | None, typer.Option("--custom-path", "-p", help="Use a custom secrets JSON file in place of the project source."),
    ] = None,
    source: Annotated[
        WritableSecretsSource | None,
        typer.Option("--source", "-s", case_sensitive=False, help="Secrets file to validate: project/p or user/u."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_secrets_file(custom_path=custom_path, source=source)
    run_managed_file_action(kind="secrets", action="validate", path=file_path)
