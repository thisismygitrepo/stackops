from pathlib import Path

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import SecretsSource


def select_secrets(
    *,
    terms: list[str] | None,
    secrets_path: Path | None,
    secrets_source: SecretsSource | None,
    interactive: bool,
    all_matches: bool,
    json_output: bool,
    preview_secrets: bool,
    verbose: bool,
    login_name: str | None,
    secret_name: str | None,
    tags: list[str] | None,
    login_tags: list[str] | None,
    secret_tags: list[str] | None,
    scopes: list[str] | None,
    keys: list[str] | None,
    load_environment: bool,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
        SecretSelectionMode,
        SecretSelectors,
        merge_candidate_key_values,
        resolve_secret_candidates,
    )
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_json import render_secret_search_json
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import (
        candidate_source_path,
        clean_optional_selector,
        clean_selector_values,
        echo_jq_login_entry_hint,
        echo_verbose_selection,
        fail,
        load_secret_candidates_from_sources,
        resolve_secret_sources,
    )

    if all_matches and interactive:
        fail("--all-matches/-a cannot be combined with --interactive/-i.")
    if preview_secrets and not interactive:
        fail("--preview-secrets only applies with --interactive/-i.")
    if json_output and verbose:
        fail("--json/-j cannot be combined with --verbose/-v because JSON output must contain only JSON.")

    secret_sources = resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    candidates = load_secret_candidates_from_sources(secret_sources)
    selectors = SecretSelectors(
        login_name=clean_optional_selector(login_name),
        secret_name=clean_optional_selector(secret_name),
        tags=clean_selector_values(tags),
        login_tags=clean_selector_values(login_tags),
        secret_tags=clean_selector_values(secret_tags),
        scopes=clean_selector_values(scopes),
        keys=clean_selector_values(keys),
    )
    selection_mode: SecretSelectionMode = "interactive" if interactive else "all" if all_matches else "unique"
    selected_candidates = resolve_secret_candidates(
        candidates=candidates, terms=terms, selectors=selectors, selection_mode=selection_mode, preview_secrets=preview_secrets
    )
    if json_output:
        typer.echo(render_secret_search_json(selected_candidates), nl=False)
        return

    if not load_environment:
        for candidate in selected_candidates:
            selected_source_path = candidate_source_path(candidate=candidate, secret_sources=secret_sources)
            typer.echo(f"""{candidate.login_name} / {candidate.secret_name} [{candidate.source_name}]""")
            typer.echo(f"""  Environment keys: {", ".join(candidate.key_values)}""")
            if verbose:
                echo_verbose_selection(candidate=candidate, secrets_path=selected_source_path)
        return

    if interactive:
        candidate = selected_candidates[0]
        selected_source_path = candidate_source_path(candidate=candidate, secret_sources=secret_sources)
        echo_jq_login_entry_hint(candidate=candidate, secrets_path=selected_source_path)
    key_values = merge_candidate_key_values(selected_candidates)
    secret_actions.validate_env_names(key_values)
    secret_actions.write_env_handoff(key_values, verbose=verbose)
    if verbose:
        for candidate in selected_candidates:
            selected_source_path = candidate_source_path(candidate=candidate, secret_sources=secret_sources)
            echo_verbose_selection(candidate=candidate, secrets_path=selected_source_path)

    variable_noun = "variable" if len(key_values) == 1 else "variables"
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Prepared {len(key_values)} environment {variable_noun}"
    if all_matches:
        bundle_noun = "bundle" if len(selected_candidates) == 1 else "bundles"
        msg += f" from {len(selected_candidates)} matching secret {bundle_noun}"
    typer.echo(f"{msg}: {', '.join(key_values)}.")

