import json
from pathlib import Path
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import WritableSecretsSource


def resolve_secrets_file(*, path: Path | None, source: WritableSecretsSource | None) -> Path:
    if path is not None:
        if source in {"global", "g"}:
            raise typer.BadParameter("--path overrides only the local secrets source; it cannot be combined with --source global.")
        return path.expanduser().absolute()
    if source is None:
        raise typer.BadParameter("Provide --path or --source local|global. Use devops vault secrets path to see both files.")
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_single_secret_source

    return resolve_single_secret_source(secrets_path=None, secrets_source=source).path


def path_secrets(
    path: Annotated[
        Path | None, typer.Option("--path", "-p", help="Override the local secrets JSON file path."),
    ] = None,
    source: Annotated[
        WritableSecretsSource | None,
        typer.Option("--source", "-s", case_sensitive=False, help="Show local/l or global/g paths. Omit to show both."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    if path is not None or source is not None:
        file_path = resolve_secrets_file(path=path, source=source)
        run_managed_file_action(kind="secrets", action="path", path=file_path)
        return

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_secret_sources
    from stackops.utils.managed_file_operations import describe_managed_file
    from stackops.utils.managed_files import get_managed_file_spec

    spec = get_managed_file_spec("secrets")
    paths = {
        secret_source.name: describe_managed_file(spec=spec, data_path=secret_source.path)
        for secret_source in resolve_secret_sources(secrets_path=None, secrets_source="both")
    }
    typer.echo(json.dumps(paths, indent=2))


def init_secrets(
    path: Annotated[
        Path | None, typer.Option("--path", "-p", help="Override the local secrets JSON file path."),
    ] = None,
    source: Annotated[
        WritableSecretsSource | None,
        typer.Option("--source", "-s", case_sensitive=False, help="Secrets file to initialize: local/l or global/g."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_secrets_file(path=path, source=source)
    run_managed_file_action(kind="secrets", action="init", path=file_path)


def validate_secrets(
    path: Annotated[
        Path | None, typer.Option("--path", "-p", help="Override the local secrets JSON file path."),
    ] = None,
    source: Annotated[
        WritableSecretsSource | None,
        typer.Option("--source", "-s", case_sensitive=False, help="Secrets file to validate: local/l or global/g."),
    ] = None,
) -> None:
    from stackops.utils.managed_file_cli import run_managed_file_action

    file_path = resolve_secrets_file(path=path, source=source)
    run_managed_file_action(kind="secrets", action="validate", path=file_path)
