import json
import sys
from contextlib import redirect_stdout
from functools import partial
from pathlib import Path
from typing import Annotated, cast

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import WritableSecretsSource
from stackops.utils.cli_utils.interaction import is_interactive


def add(
    custom_path: Annotated[
        Path | None, typer.Option("--custom-path", "-p", help="Use only this secrets JSON file, overriding --source.")
    ] = None,
    secrets_source: Annotated[
        WritableSecretsSource,
        typer.Option(
            "--source", "-s", case_sensitive=False,
            help="Secrets file to update: workspace/w or user/u. Ignored when --custom-path is provided.",
        ),
    ] = "workspace",
    create: Annotated[
        bool, typer.Option("--create", "-c", help="Allow creating a missing secrets JSON file and its schema.")
    ] = False,
    input_path: Annotated[
        str | None,
        typer.Option("--input", "-i", help="Read one login JSON object from a file, or - for stdin, without prompts. Use --schema for its format."),
    ] = None,
    schema: Annotated[
        bool, typer.Option("--schema", "-S", help="Print the input JSON Schema and exit without accessing the vault.")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", "-j", help="Print a JSON result without secret values. Requires --input and never prompts.")
    ] = False,
    non_interactive: Annotated[
        bool, typer.Option("--non-interactive", "-n", help="Require --input and never prompt, even in a terminal.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", "-d", help="Validate the entry and destination without writing the secrets file or schema.")
    ] = False,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_actions import add_secrets_entry
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_prompts import prompt_secret_login
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import resolve_single_secret_source

    if schema:
        _print_input_schema()
        return
    if input_path is None and (non_interactive or json_output or not is_interactive()):
        raise typer.BadParameter("Provide --input FILE or --input - for stdin. Use --schema to inspect the login JSON format.")
    if input_path == "-" and sys.stdin.isatty():
        raise typer.BadParameter("--input - requires piped or redirected JSON on stdin.")

    with redirect_stdout(sys.stderr):
        secret_source = resolve_single_secret_source(secrets_path=custom_path, secrets_source=secrets_source)
    read_entry = partial(_read_input_entry, input_path) if input_path is not None else prompt_secret_login
    try:
        entry = add_secrets_entry(secrets_path=secret_source.path, read_entry=read_entry, create=create, dry_run=dry_run)
    except UnicodeError as error:
        typer.echo("Error: Secrets input and destination must contain UTF-8 text.", err=True)
        raise typer.Exit(code=1) from error
    except (OSError, ValueError) as error:
        typer.echo(f"""Error: {error}""", err=True)
        raise typer.Exit(code=1) from error

    if json_output:
        typer.echo(json.dumps({"status": "validated" if dry_run else "added", "name": entry["name"], "path": str(secret_source.path)}))
    else:
        action = "Validated" if dry_run else "Added"
        typer.echo(f"""{action} secrets entry '{entry['name']}' {'for' if dry_run else 'to'} {secret_source.path}""")


def _read_input_entry(input_path: str) -> object:
    raw = sys.stdin.read() if input_path == "-" else Path(input_path).expanduser().read_text(encoding="utf-8")
    try:
        payload: object = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"""Invalid input JSON: {error.msg} at line {error.lineno}, column {error.colno}.""") from error
    return payload


def _print_input_schema() -> None:
    import stackops.secrets.assets as secrets_assets
    from stackops.utils.path_reference import get_path_reference_path

    schema_path = get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE)
    catalog_schema = cast(dict[str, object], json.loads(schema_path.read_text(encoding="utf-8")))
    input_schema = {"$schema": catalog_schema["$schema"], "$ref": "#/definitions/login", "definitions": catalog_schema["definitions"]}
    typer.echo(json.dumps(input_schema, indent=2))
