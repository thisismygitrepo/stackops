from pathlib import Path
from typing import Annotated, Literal, TypedDict

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import SecretCandidate
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource

SECRETS_DELETE_HELP = "Remove secret bundles, whole logins, or single keys from a secrets file."
SECRETS_DELETE_EPILOG = """Examples:
  devops vault delete --name github-personal --dry-run
  devops vault delete --source user --name aws-dev --secret-name iam-access-key --yes
  devops vault delete --name aws-dev --all-matches --yes --json
  devops vault delete --name aws-dev --key AWS_SESSION_TOKEN --yes

Selection works as in devops vault load and must match exactly one bundle unless --all-matches is given.
The matching bundle is removed. With --key, only those keys are removed and the bundle is kept.
A login left without a bundle is removed too, so --name LOGIN --all-matches removes a whole login.
A secrets file left without a login is deleted; devops vault add --create starts it again.
Without --yes, the selection is listed and confirmed in a terminal. Values are never printed.
Use devops vault add --replace to change a login in place.
"""


class DeletedBundle(TypedDict):
    login: str
    secret: str
    keys: list[str]


class DeletionReceipt(TypedDict):
    status: Literal["deleted", "validated"]
    removed: Literal["bundles", "keys"]
    bundles: list[DeletedBundle]
    logins_removed: list[str]
    file_removed: bool
    path: str


def delete(
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
            help="Secrets file source to search: workspace/w, user/u, or all/a. The selection must sit in one file, which is the one updated.",
        ),
    ] = None,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Choose the secret bundle with a TV fuzzy picker.")] = False,
    preview_secrets: Annotated[
        bool, typer.Option("--preview-secrets", "-P", help="Include secret values in the interactive TV preview. Only applies with --interactive/-i.")
    ] = False,
    all_matches: Annotated[bool, typer.Option("--all-matches", "-a", help="Remove every matching secret bundle instead of requiring exactly one.")] = False,
    login_name: Annotated[str | None, typer.Option("--name", "-n", help="Exact login name at entries[].name to require.")] = None,
    secret_name: Annotated[str | None, typer.Option("--secret-name", "-N", help="Exact entries[].secrets[].name value to require.")] = None,
    tags: Annotated[list[str] | None, typer.Option("--tag", "--tags", "-t", help="Exact login or secret tag to require. Repeat for multiple tags.")] = None,
    login_tags: Annotated[list[str] | None, typer.Option("--login-tag", "-l", help="Exact login tag at entries[].tags to require. Repeat for multiple tags.")] = None,
    secret_tags: Annotated[
        list[str] | None, typer.Option("--secret-tag", "-T", help="Exact entries[].secrets[].tags value to require. Repeat for multiple tags.")
    ] = None,
    scopes: Annotated[list[str] | None, typer.Option("--scope", "-S", help="Exact entries[].secrets[].scopes value to require. Repeat for multiple scopes.")] = None,
    keys: Annotated[
        list[str] | None,
        typer.Option("--key", "-k", help="Exact env var key in keyValues to require. Only these keys are removed, and the bundle is kept. Repeat for multiple keys."),
    ] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", "-d", help="List what would be removed without writing the secrets file.")] = False,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Delete without confirmation.")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print a JSON receipt without secret values. Requires --yes or --dry-run.")] = False,
) -> None:
    import json
    import sys
    from collections import Counter
    from contextlib import redirect_stdout

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_selection import SecretSelectionRequest, resolve_selection
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import candidate_source_path, clean_selector_values, fail
    from stackops.utils.cli_utils.interaction import require_interactive

    confirm = not (yes or dry_run)
    if confirm and json_output:
        raise typer.BadParameter("--json never prompts. Add --yes to delete, or --dry-run to list what would be removed.")
    if confirm:
        require_interactive("Confirming a deletion without --yes or --dry-run")

    with redirect_stdout(sys.stderr):
        selection = resolve_selection(
            SecretSelectionRequest(
                terms=terms, secrets_path=custom_path, secrets_source=secrets_source, interactive=interactive, all_matches=all_matches,
                preview_secrets=preview_secrets, login_name=login_name, secret_name=secret_name, tags=tags, login_tags=login_tags,
                secret_tags=secret_tags, scopes=scopes, keys=keys,
            )
        )
        candidates = selection.candidates
        secrets_paths = sorted({candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources) for candidate in candidates})
        if len(secrets_paths) > 1:
            fail(
                f"""The selection spans {len(secrets_paths)} secrets files: {", ".join(str(path) for path in secrets_paths)}. """
                + "Choose one with --source or --custom-path."
            )
        secrets_path = secrets_paths[0]
        removed_keys = tuple(dict.fromkeys(clean_selector_values(keys)))
        selected_per_login = Counter(candidate.entry_index for candidate in candidates)
        emptied_logins: dict[int, str] = {} if removed_keys else {
            candidate.entry_index: candidate.login_name
            for candidate in candidates
            if selected_per_login[candidate.entry_index] == len(candidate.login_entry["secrets"])
        }
        receipt: DeletionReceipt = {
            "status": "validated" if dry_run else "deleted",
            "removed": "keys" if removed_keys else "bundles",
            "bundles": [
                {"login": candidate.login_name, "secret": candidate.secret_name, "keys": list(removed_keys or candidate.key_values)}
                for candidate in candidates
            ],
            "logins_removed": list(emptied_logins.values()),
            "file_removed": len(emptied_logins) == len(candidates[0].secrets_file["entries"]),
            "path": str(secrets_path),
        }
        if confirm:
            typer.echo(_render_receipt(receipt=receipt, heading="Selected for deletion from"))
            if not typer.confirm("Delete these now? This cannot be undone.", default=False, err=True):
                typer.echo("Nothing was deleted.")
                raise typer.Exit(code=1)
        if not dry_run:
            _apply_deletion(secrets_path=secrets_path, candidates=candidates, removed_keys=removed_keys)

    if json_output:
        typer.echo(json.dumps(receipt))
        return
    typer.echo(_render_receipt(receipt=receipt, heading="Would delete from" if dry_run else "Deleted from"))


def _render_receipt(*, receipt: DeletionReceipt, heading: str) -> str:
    lines = [f"""{heading} {receipt["path"]}:"""]
    for bundle in receipt["bundles"]:
        bundle_keys = ", ".join(bundle["keys"]) or "<no keys>"
        match receipt["removed"]:
            case "keys":
                lines.append(f"""  keys {bundle_keys} of {bundle["login"]} / {bundle["secret"]}""")
            case "bundles":
                lines.append(f"""  bundle {bundle["login"]} / {bundle["secret"]} ({bundle_keys})""")
    lines.extend(f"""  login {login_name}, left without a bundle""" for login_name in receipt["logins_removed"])
    if receipt["file_removed"]:
        lines.append("  the file itself, left without a login")
    return "\n".join(lines)


def _apply_deletion(*, secrets_path: Path, candidates: tuple[SecretCandidate, ...], removed_keys: tuple[str, ...]) -> None:
    import json
    from typing import cast

    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import fail
    from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
    from stackops.secrets.models import SecretsFile
    from stackops.secrets.writer import replace_secrets_file

    try:
        if load_secrets_file(secrets_path) != candidates[0].secrets_file:
            fail(f"""{secrets_path} changed on disk after the selection was made. Nothing was deleted; run the command again.""")
        secrets_file = cast(SecretsFile, json.loads(secrets_path.read_text(encoding="utf-8")))
        entries = secrets_file["entries"]
        if removed_keys:
            for candidate in candidates:
                key_values = entries[candidate.entry_index]["secrets"][candidate.secret_index]["keyValues"]
                for key in removed_keys:
                    del key_values[key]
        else:
            for candidate in sorted(candidates, key=lambda candidate: (candidate.entry_index, candidate.secret_index), reverse=True):
                del entries[candidate.entry_index]["secrets"][candidate.secret_index]
            entries[:] = [entry for entry in entries if entry["secrets"]]
        if entries:
            replace_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file)
        else:
            secrets_path.unlink()
    except SecretsSchemaError as error:
        fail(f"""Nothing was deleted from {secrets_path}: {error}""")
