from datetime import date
import subprocess
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_devops.stackops_release import (
    bump_stackops_version,
    is_stackops_repository,
)
from stackops.utils.source_of_truth import STACKOPS_REPO_DIR


def release(
    publish: Annotated[
        bool,
        typer.Option(
            "--publish",
            "-p",
            help="Commit the release changes and push main with its version tag to origin. Requires a clean main branch synchronized with origin.",
        ),
    ] = False,
) -> None:
    """Bump the calendar version and update StackOps version references.

    Developer only: operates on the Git checkout at ~/code/stackops.
    Without --publish, leaves the release changes uncommitted for review.
    """
    try:
        if not is_stackops_repository(repo_root=STACKOPS_REPO_DIR):
            raise ValueError(f"""Release requires a StackOps Git checkout at {STACKOPS_REPO_DIR}.""")
        today = date.today()
        publication = None
        if publish:
            from stackops.scripts.python.helpers.helpers_devops.stackops_publish import prepare_stackops_publication

            publication = prepare_stackops_publication(repo_root=STACKOPS_REPO_DIR, today=today)
        prepared_release = bump_stackops_version(repo_root=STACKOPS_REPO_DIR, today=today)
        typer.echo(f"""Prepared StackOps {prepared_release.previous_version} → {prepared_release.version}.""")
        for changed_file in prepared_release.changed_files:
            typer.echo(f"""Updated {changed_file.as_posix()}""")
        if publication is None:
            typer.echo("Release changes are ready for review and commit.")
            return
        from stackops.scripts.python.helpers.helpers_devops.stackops_publish import publish_stackops_release

        release_tag = publish_stackops_release(
            repo_root=STACKOPS_REPO_DIR,
            release=prepared_release,
            publication=publication,
        )
        typer.echo(f"""Pushed {release_tag} and main. The existing GitHub workflow will publish the release.""")
    except (ValueError, RuntimeError, OSError, subprocess.CalledProcessError) as error:
        typer.echo(f"""Release failed: {error}""", err=True)
        raise typer.Exit(code=1) from None
