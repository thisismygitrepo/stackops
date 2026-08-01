from typing import NoReturn

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_constants import CANDIDATE_DISPLAY_LIMIT


def fail_conflicting_environment_merge(
    *,
    selected_bundle_count: int,
    conflicting_variable_names: tuple[str, ...],
    conflicting_bundle_rows: tuple[str, ...],
) -> NoReturn:
    variable_noun = "variable" if len(conflicting_variable_names) == 1 else "variables"
    typer.echo(
        typer.style("Error: ", fg=typer.colors.RED)
        + f"Cannot merge {selected_bundle_count} matching secret bundles: "
        + f"{len(conflicting_variable_names)} environment {variable_noun} would receive different values."
    )
    typer.echo(
        "--all-matches/-a builds one environment from every match. "
        "A repeated variable name is valid only when every bundle gives it the same value."
    )
    typer.echo()
    typer.echo("Conflicting environment variables:")
    typer.echo(f"  {', '.join(conflicting_variable_names)}")
    typer.echo("Conflicting bundles (secret values hidden):")
    for row in conflicting_bundle_rows[:CANDIDATE_DISPLAY_LIMIT]:
        typer.echo(f"  - {row}")
    hidden_bundle_count = len(conflicting_bundle_rows) - CANDIDATE_DISPLAY_LIMIT
    if hidden_bundle_count > 0:
        typer.echo(f"  ... {hidden_bundle_count} more conflicting bundles")

    typer.echo()
    typer.echo("Choose what you intended:")
    typer.echo("  - JSON with every bundle: add --json/-j; bundles remain separate, so repeated names do not collide.")
    typer.echo("  - One bundle: replace --all-matches/-a with --interactive/-i.")
    typer.echo("  - A smaller merge: narrow the search or add exact selectors such as --name/-n and --secret-name/-N.")
    typer.echo("  - All bundles: rename the conflicting keyValues keys so each environment variable has only one value.")
    raise typer.Exit(code=1)
