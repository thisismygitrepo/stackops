#!/usr/bin/env -S uv run --no-dev --project

"""preview - File preview and backend launcher."""

from typing import Annotated, cast
import typer
from stackops.scripts.python.enums import BACKENDS, BACKENDS_LOOSE, BACKENDS_MAP

BASE_INTERACTIVE_BACKENDS: tuple[str, ...] = (
    "ipython",
    "python",
    "marimo",
    "jupyter",
    "vscode",
    "visidata",
)
AUTO_PATH_BACKENDS: tuple[str, ...] = (
    "auto",
    "preview",
)
FILE_VIEWER_BACKENDS: tuple[str, ...] = (
    "browser",
    "glow",
)


def _database_backends() -> tuple[str, ...]:
    from stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend import BACKEND_CHOICES

    return BACKEND_CHOICES


def _interactive_backend_options(path: str | None) -> list[str]:
    options = [str(backend) for backend in BASE_INTERACTIVE_BACKENDS]
    if path is None:
        return options

    options.extend(AUTO_PATH_BACKENDS)
    options.extend(FILE_VIEWER_BACKENDS)
    options.extend(_database_backends())
    return options


def _resolve_backend_choice(backend: BACKENDS_LOOSE) -> BACKENDS:
    return BACKENDS_MAP[backend]


def _choose_backend_interactively(path: str | None) -> BACKENDS:
    from stackops.utils.options import choose_from_options

    choice = choose_from_options(
        options=_interactive_backend_options(path=path),
        msg="Select preview backend",
        multi=False,
        custom_input=False,
        default="ipython",
        tv=True,
    )
    if choice is None:
        typer.echo("Error: no backend selected.", err=True, color=True)
        raise typer.Exit(code=1)
    return _resolve_backend_choice(backend=cast(BACKENDS_LOOSE, str(choice)))


def preview(
    path: Annotated[str | None, typer.Argument(help="path of file to read.")] = None,
    project_path: Annotated[str | None, typer.Option("--project", "-p", help="specify uv project to use")] = None,
    uv_with: Annotated[str | None, typer.Option("--uv-with", "-w", help="specify uv with packages to use")] = None,
    backend: Annotated[BACKENDS_LOOSE, typer.Option("--backend", "-b", help="specify the backend to use")] = "ipython",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="select the backend interactively")] = False,
    profile: Annotated[str | None, typer.Option("--profile", "-r", help="ipython profile to use, defaults to default profile.")] = None,
    stackops_project: Annotated[bool, typer.Option("--self", "-s", help="specify stackops project to use.")] = False,
    frozen: Annotated[bool, typer.Option("--frozen", "-f", help="freeze the environment (no package changes allowed)")] = False
) -> None:
    """Preview files and launch reader backends."""
    if stackops_project:
        from pathlib import Path
        if Path.home().joinpath("code/stackops").exists():
            project_path = str(Path.home().joinpath("code/stackops"))
        else:
            pass
    resolved_backend: BACKENDS
    if interactive:
        resolved_backend = _choose_backend_interactively(path=path)
    else:
        resolved_backend = _resolve_backend_choice(backend=backend)

    from stackops.scripts.python.helpers.helpers_preview.preview_impl import preview as impl
    impl(
        path=path,
        project_path=project_path,
        uv_with=uv_with,
        backend=resolved_backend,
        profile=profile,
        frozen=frozen,
    )


def main() -> None:
    typer.run(preview)


if __name__ == "__main__":
    main()
