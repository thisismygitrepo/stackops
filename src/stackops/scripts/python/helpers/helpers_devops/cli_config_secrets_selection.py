import sys
from contextlib import nullcontext, redirect_stdout
from dataclasses import dataclass
from pathlib import Path

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretCandidate,
    SecretSelectionMode,
    SecretSelectors,
    merge_candidate_key_values,
    resolve_secret_candidates,
)
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_json import render_secret_search_json
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import (
    SecretsFileSource,
    candidate_source_path,
    clean_optional_selector,
    clean_selector_values,
    echo_jq_login_entry_hint,
    echo_verbose_selection,
    fail,
    load_secret_candidates_from_sources,
    resolve_secret_sources,
)


@dataclass(frozen=True)
class SecretSelectionRequest:
    terms: list[str] | None
    secrets_path: Path | None
    secrets_source: SecretsSource | None
    interactive: bool
    all_matches: bool
    preview_secrets: bool
    login_name: str | None
    secret_name: str | None
    tags: list[str] | None
    login_tags: list[str] | None
    secret_tags: list[str] | None
    scopes: list[str] | None
    keys: list[str] | None


@dataclass(frozen=True)
class SecretSelection:
    candidates: tuple[SecretCandidate, ...]
    secret_sources: list[SecretsFileSource]


def resolve_selection(request: SecretSelectionRequest) -> SecretSelection:
    if request.all_matches and request.interactive:
        fail("--all-matches/-a cannot be combined with --interactive/-i.")
    if request.preview_secrets and not request.interactive:
        fail("--preview-secrets only applies with --interactive/-i.")

    secret_sources = resolve_secret_sources(secrets_path=request.secrets_path, secrets_source=request.secrets_source)
    selectors = SecretSelectors(
        login_name=clean_optional_selector(request.login_name),
        secret_name=clean_optional_selector(request.secret_name),
        tags=clean_selector_values(request.tags),
        login_tags=clean_selector_values(request.login_tags),
        secret_tags=clean_selector_values(request.secret_tags),
        scopes=clean_selector_values(request.scopes),
        keys=clean_selector_values(request.keys),
    )
    selection_mode: SecretSelectionMode = "interactive" if request.interactive else "all" if request.all_matches else "unique"
    candidates = resolve_secret_candidates(
        candidates=load_secret_candidates_from_sources(secret_sources),
        terms=request.terms,
        selectors=selectors,
        selection_mode=selection_mode,
        preview_secrets=request.preview_secrets,
    )
    return SecretSelection(candidates=candidates, secret_sources=secret_sources)


def search_secrets(request: SecretSelectionRequest, *, json_output: bool, verbose: bool, load_environment: bool, copy_key: str | None) -> None:
    import os

    from stackops.scripts.python.helpers.helpers_devops.vault_clipboard import copy_secret, require_clipboard
    from stackops.secrets.search import render_secret_value

    with redirect_stdout(sys.stderr) if json_output else nullcontext():
        if json_output and verbose:
            fail("--json/-j cannot be combined with --verbose/-v because JSON output must contain only JSON.")
        if json_output and request.interactive:
            fail("--json/-j cannot be combined with --interactive/-i. Use exact selectors or --all-matches instead.")
        if json_output and load_environment:
            fail("--json/-j cannot be combined with --load/-L because JSON output must contain only JSON.")
        if json_output and copy_key is not None:
            fail("--json/-j cannot be combined with --copy/-C because JSON output must contain only JSON.")
        if load_environment and not os.environ.get("OP_PROGRAM_PATH"):
            raise typer.BadParameter(
                "--load/-L defines variables in the calling shell, so invoke search through the StackOps shell wrapper. "
                + "To run one program with the secrets, use devops vault load --command 'PROGRAM ARGUMENTS'."
            )
        clipboard = require_clipboard() if copy_key is not None else None
        selection = resolve_selection(request)
    if json_output:
        typer.echo(render_secret_search_json(selection.candidates), nl=False)
        return

    for candidate in selection.candidates:
        typer.echo(f"""{candidate.login_name} / {candidate.secret_name} [{candidate.source_name}]""")
        typer.echo(f"""  Environment keys: {", ".join(candidate.key_values)}""")
        if verbose:
            echo_verbose_selection(
                candidate=candidate, secrets_path=candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources)
            )
    if copy_key is not None and clipboard is not None:
        key_values = merge_candidate_key_values(selection.candidates)
        if copy_key not in key_values:
            fail(f"""--copy/-C {copy_key} is not an environment key of the selection. Available keys: {", ".join(key_values)}""")
        copy_secret(clipboard, render_secret_value(key_values[copy_key]), label=copy_key)
    if not load_environment:
        if copy_key is None:
            typer.echo("""Nothing was loaded. Add --load/-L, or use "devops vault load" with the same arguments, to define these variables.""", err=True)
        return
    prepare_shell_environment(selection.candidates, all_matches=request.all_matches, verbose=verbose)


def prepare_shell_environment(candidates: tuple[SecretCandidate, ...], *, all_matches: bool, verbose: bool) -> None:
    from stackops.scripts.python.helpers.helpers_devops import vault_environment

    origin = f"""{len(candidates)} matching secret {"bundle" if len(candidates) == 1 else "bundles"}""" if all_matches else None
    vault_environment.prepare_shell_environment(merge_candidate_key_values(candidates), origin=origin, verbose=verbose)


def load_secrets(request: SecretSelectionRequest, *, verbose: bool, command: str | None) -> None:
    from stackops.scripts.python.helpers.helpers_devops.vault_environment import parse_load_command, run_command_with_environment

    command_args = parse_load_command(command)
    with redirect_stdout(sys.stderr):
        selection = resolve_selection(request)
    if request.interactive:
        candidate = selection.candidates[0]
        echo_jq_login_entry_hint(
            candidate=candidate, secrets_path=candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources)
        )
    if command_args is not None:
        run_command_with_environment(command_args, merge_candidate_key_values(selection.candidates))
    if verbose:
        for candidate in selection.candidates:
            echo_verbose_selection(
                candidate=candidate, secrets_path=candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources)
            )
    prepare_shell_environment(selection.candidates, all_matches=request.all_matches, verbose=verbose)
