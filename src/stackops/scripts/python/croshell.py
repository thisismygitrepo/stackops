#!/usr/bin/env -S uv run --no-dev --project

"""croshell - Cross-shell command execution."""

from typing import Annotated
import typer
from stackops.scripts.python.enums import BACKENDS_LOOSE, BACKENDS_MAP


def croshell(
    path: Annotated[str | None, typer.Argument(help="path of file to read.")] = None,
    project_path: Annotated[str | None, typer.Option("--project", "-p", help="specify uv project to use")] = None,
    uv_with: Annotated[str | None, typer.Option("--uv-with", "-w", help="specify uv with packages to use")] = None,
    backend: Annotated[BACKENDS_LOOSE, typer.Option("--backend", "-b", help="specify the backend to use")] = "ipython",
    profile: Annotated[str | None, typer.Option("--profile", "-r", help="ipython profile to use, defaults to default profile.")] = None,
    stackops_project: Annotated[bool, typer.Option("--self", "-s", help="specify stackops project to use.")] = False,
    frozen: Annotated[bool, typer.Option("--frozen", "-f", help="freeze the environment (no package changes allowed)")] = False
) -> None:
    """Cross-shell command execution."""
    if stackops_project:
        from pathlib import Path
        if Path.home().joinpath("code/stackops").exists():
            project_path = str(Path.home().joinpath("code/stackops"))
        else:
            pass
    from stackops.scripts.python.helpers.helpers_croshell.croshell_impl import croshell as impl
    impl(path=path, project_path=project_path, uv_with=uv_with, backend=BACKENDS_MAP[backend], profile=profile, frozen=frozen)


def main() -> None:
    typer.run(croshell)


if __name__ == "__main__":
    main()
