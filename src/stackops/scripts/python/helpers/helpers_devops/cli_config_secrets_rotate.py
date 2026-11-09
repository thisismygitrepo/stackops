from pathlib import Path
from typing import Annotated, TypedDict

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import SecretCandidate
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource

SECRETS_ROTATE_HELP = "Replace values in one secret bundle and record its rotation date."
SECRETS_ROTATE_EPILOG = """Examples:
  devops vault rotate --source user --name github-personal
  devops vault rotate --name aws-dev --key AWS_SECRET_ACCESS_KEY
  devops vault rotate --name aws-dev --input new-keys.json --json

Selection works as in devops vault load and must match exactly one bundle.
Without --input, hidden prompts ask for each key (only --key keys when given); leave one blank to keep it.
--input reads a JSON object of existing keys to new values from a file, or - for stdin.
Only existing keys are replaced, and rotation.lastRotated becomes today. Values are never printed.
Edit the secrets JSON directly to add keys or change labels.
"""


class RotationReceipt(TypedDict):
    status: str
    login: str
    secret: str
    keys: list[str]
    lastRotated: str
    path: str


def rotate(
    terms: Annotated[
        list[str] | None,
        typer.Argument(
            help=(
                "Case-insensitive terms used to match secret bundles. All terms must match across login name/tags/accountName, "
                "secret name/tags/scopes, metadata, or env var keys."
            )
        ),
    ] = None,
    custom_path: Annotated[Path | None, typer.Option("--custom-path", "-p", help="Use only this secrets JSON file, overriding --source.")] = None,
    secrets_source: Annotated[
        SecretsSource | None,
        typer.Option(
            "--source", "-s", case_sensitive=False,
            help="Secrets file source to search: workspace/w, user/u, or all/a. The matching bundle's own file is updated.",
        ),
    ] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose the secret bundle with a TV fuzzy picker.")] = False,
    preview_secrets: Annotated[
        bool, typer.Option("--preview-secrets", "-P", help="Include secret values in the interactive TV preview. Only applies with --interactive/-i.")
    ] = False,
    login_name: Annotated[str | None, typer.Option("--name", "-n", help="Exact login name at entries[].name to require.")] = None,
    secret_name: Annotated[str | None, typer.Option("--secret-name", "-N", help="Exact entries[].secrets[].name value to require.")] = None,
    tags: Annotated[list[str] | None, typer.Option("--tag", "--tags", "-t", help="Exact login or secret tag to require. Repeat for multiple tags.")] = None,
    login_tags: Annotated[list[str] | None, typer.Option("--login-tag", "-l", help="Exact login tag at entries[].tags to require. Repeat for multiple tags.")] = None,
    secret_tags: Annotated[
        list[str] | None, typer.Option("--secret-tag", "-T", help="Exact entries[].secrets[].tags value to require. Repeat for multiple tags.")
    ] = None,
    scopes: Annotated[list[str] | None, typer.Option("--scope", "-S", help="Exact entries[].secrets[].scopes value to require. Repeat for multiple scopes.")] = None,
    keys: Annotated[
        list[str] | None, typer.Option("--key", "-k", help="Exact env var key in keyValues to require. Without --input, only these keys are prompted.")
    ] = None,
    input_path: Annotated[
        str | None, typer.Option("--input", "-I", help="Read a JSON object of existing keys to new values from a file, or - for stdin, without prompts.")
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-d", help="Validate the selection and new values without writing the secrets file.")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print a JSON receipt without secret values. Requires --input.")] = False,
) -> None:
    import json
    import sys
    from contextlib import redirect_stdout
    from datetime import date

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_selection import SecretSelectionRequest, resolve_selection
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import candidate_source_path, clean_selector_values
    from stackops.utils.cli_utils.interaction import is_interactive

    if input_path is None and (json_output or not is_interactive()):
        raise typer.BadParameter("Provide --input FILE or --input - for stdin with a JSON object of keys to new values.")
    if input_path == "-" and sys.stdin.isatty():
        raise typer.BadParameter("--input - requires piped or redirected JSON on stdin.")

    with redirect_stdout(sys.stderr):
        selection = resolve_selection(
            SecretSelectionRequest(
                terms=terms, secrets_path=custom_path, secrets_source=secrets_source, interactive=interactive, all_matches=False,
                preview_secrets=preview_secrets, login_name=login_name, secret_name=secret_name, tags=tags, login_tags=login_tags,
                secret_tags=secret_tags, scopes=scopes, keys=keys,
            )
        )
        candidate = selection.candidates[0]
        secrets_path = candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources)
        prompt_keys = clean_selector_values(keys) or tuple(candidate.key_values)
        replacements = _read_input_replacements(input_path) if input_path is not None else _prompt_replacements(candidate=candidate, prompt_keys=prompt_keys)
        rotated_on = date.today().isoformat()
        changed_keys = _apply_rotation(secrets_path=secrets_path, candidate=candidate, replacements=replacements, rotated_on=rotated_on, dry_run=dry_run)

    receipt: RotationReceipt = {
        "status": "validated" if dry_run else "rotated", "login": candidate.login_name, "secret": candidate.secret_name,
        "keys": changed_keys, "lastRotated": rotated_on, "path": str(secrets_path),
    }
    if json_output:
        typer.echo(json.dumps(receipt))
        return
    action = "Validated rotation of" if dry_run else "Rotated"
    typer.echo(f"""{action} {candidate.login_name} / {candidate.secret_name}: {", ".join(changed_keys)}; lastRotated {rotated_on} in {secrets_path}""")


def _read_input_replacements(input_path: str) -> dict[str, object]:
    import json
    import sys

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import fail

    raw = sys.stdin.read() if input_path == "-" else Path(input_path).expanduser().read_text(encoding="utf-8")
    try:
        payload: object = json.loads(raw)
    except json.JSONDecodeError as error:
        fail(f"""Invalid input JSON: {error.msg} at line {error.lineno}, column {error.colno}.""")
    if not isinstance(payload, dict) or not payload:
        fail("Input must be a non-empty JSON object mapping existing keyValues keys to new values.")
    return {str(key): value for key, value in payload.items()}


def _prompt_replacements(*, candidate: SecretCandidate, prompt_keys: tuple[str, ...]) -> dict[str, object]:
    typer.echo(f"""Rotating {candidate.login_name} / {candidate.secret_name}. Leave a value blank to keep it.""")
    replacements: dict[str, object] = {}
    for key in prompt_keys:
        while True:
            value = str(typer.prompt(f"New value for {key}", default="", hide_input=True, show_default=False))
            if not value or str(typer.prompt(f"Repeat new value for {key}", default="", hide_input=True, show_default=False)) == value:
                break
            typer.echo(f"Values for {key} did not match. Try again, or leave it blank to keep the current value.")
        if value:
            replacements[key] = value
    return replacements


def _apply_rotation(*, secrets_path: Path, candidate: SecretCandidate, replacements: dict[str, object], rotated_on: str, dry_run: bool) -> list[str]:
    import json
    from typing import cast

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import fail
    from stackops.secrets.loader import SecretsSchemaError
    from stackops.secrets.models import SecretsFile
    from stackops.secrets.writer import replace_secrets_file

    unknown_keys = [key for key in replacements if key not in candidate.key_values]
    if unknown_keys:
        fail(
            f"""Key(s) not in {candidate.login_name} / {candidate.secret_name}: {", ".join(unknown_keys)}. """
            + f"""Existing keys: {", ".join(candidate.key_values)}."""
        )
    changed_keys = [key for key, value in replacements.items() if candidate.key_values[key] != value]
    if not changed_keys:
        fail("No values changed; the secrets file was not modified.")
    secrets_file = cast(SecretsFile, json.loads(secrets_path.read_text(encoding="utf-8")))
    secret = secrets_file["entries"][candidate.entry_index]["secrets"][candidate.secret_index]
    for key in changed_keys:
        secret["keyValues"][key] = replacements[key]
    secret["rotation"] = {**secret.get("rotation", {}), "lastRotated": rotated_on}
    if not dry_run:
        try:
            replace_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file)
        except SecretsSchemaError as error:
            fail(f"""Rotated secrets file failed validation; {secrets_path} was not modified: {error}""")
    return changed_keys
