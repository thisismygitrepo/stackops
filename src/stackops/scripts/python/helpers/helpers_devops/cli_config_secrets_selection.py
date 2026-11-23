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


def search_secrets(request: SecretSelectionRequest, *, json_output: bool, verbose: bool, load_environment: bool) -> None:
    import os

    with redirect_stdout(sys.stderr) if json_output else nullcontext():
        if json_output and verbose:
            fail("--json/-j cannot be combined with --verbose/-v because JSON output must contain only JSON.")
        if json_output and request.interactive:
            fail("--json/-j cannot be combined with --interactive/-i. Use exact selectors or --all-matches instead.")
        if json_output and load_environment:
            fail("--json/-j cannot be combined with --load/-L because JSON output must contain only JSON.")
        if load_environment and not os.environ.get("OP_PROGRAM_PATH"):
            raise typer.BadParameter(
                "--load/-L defines variables in the calling shell, so invoke search through the StackOps shell wrapper. "
                + "To run one program with the secrets, use devops vault load --command 'PROGRAM ARGUMENTS'."
            )
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
    if not load_environment:
        typer.echo("""Nothing was loaded. Add --load/-L, or use "devops vault load" with the same arguments, to define these variables.""", err=True)
        return
    prepare_shell_environment(selection.candidates, all_matches=request.all_matches, verbose=verbose)


def prepare_shell_environment(candidates: tuple[SecretCandidate, ...], *, all_matches: bool, verbose: bool) -> None:
    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions

    key_values = merge_candidate_key_values(candidates)
    secret_actions.validate_env_names(key_values)
    secret_actions.write_env_handoff(key_values, verbose=verbose)
    variable_noun = "variable" if len(key_values) == 1 else "variables"
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(key_values)} environment {variable_noun}"
    if all_matches:
        bundle_noun = "bundle" if len(candidates) == 1 else "bundles"
        msg += f" from {len(candidates)} matching secret {bundle_noun}"
    typer.echo(f"{msg}: {', '.join(key_values)}.")


def load_secrets(request: SecretSelectionRequest, *, verbose: bool, command: str | None) -> None:
    import os
    import shlex
    import subprocess

    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
    from stackops.secrets.search import render_secret_value

    try:
        command_args = shlex.split(command) if command is not None else None
    except ValueError as error:
        raise typer.BadParameter("--command contains invalid argument quoting.") from error
    if command_args == []:
        raise typer.BadParameter("--command must contain an executable.")
    if command_args is None and not os.environ.get("OP_PROGRAM_PATH"):
        raise typer.BadParameter("Use --command 'PROGRAM ARGUMENTS' to run with secrets, or invoke load through the StackOps shell wrapper.")
    with redirect_stdout(sys.stderr):
        selection = resolve_selection(request)
    if request.interactive:
        candidate = selection.candidates[0]
        echo_jq_login_entry_hint(
            candidate=candidate, secrets_path=candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources)
        )
    if command_args is not None:
        key_values = merge_candidate_key_values(selection.candidates)
        secret_actions.validate_env_names(key_values)
        environment = os.environ.copy()
        environment.update({key: render_secret_value(value) for key, value in key_values.items()})
        try:
            result = subprocess.run(command_args, env=environment, check=False)
        except OSError as error:
            typer.echo(f"Could not start child command: {error.strerror}", err=True)
            raise typer.Exit(code=1) from error
        raise typer.Exit(code=result.returncode if result.returncode >= 0 else 128 - result.returncode)
    if verbose:
        for candidate in selection.candidates:
            echo_verbose_selection(
                candidate=candidate, secrets_path=candidate_source_path(candidate=candidate, secret_sources=selection.secret_sources)
            )
    prepare_shell_environment(selection.candidates, all_matches=request.all_matches, verbose=verbose)
