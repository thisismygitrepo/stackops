#!/usr/bin/env -S uv run --no-dev --project

"""croshell - Cross-shell command execution."""

from typing import Annotated, Literal, cast
import typer
from stackops.scripts.python.enums import BACKENDS_LOOSE, BACKENDS_MAP

Auto2Mode = Literal["auto", "browser", "markdown", "database", "visidata"]
InteractiveBackendSelection = tuple[BACKENDS_LOOSE, Auto2Mode, str]


BASE_INTERACTIVE_BACKENDS: tuple[BACKENDS_LOOSE, ...] = (
    "ipython",
    "python",
    "marimo",
    "jupyter",
    "vscode",
    "visidata",
)
AUTO2_TOOL_BACKENDS: tuple[str, ...] = (
    "browser",
    "glow",
)


def _interactive_backend_options(path: str | None) -> list[str]:
    options = [str(backend) for backend in BASE_INTERACTIVE_BACKENDS]
    if path is None:
        return options

    from stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend import BACKEND_CHOICES

    options.extend(AUTO2_TOOL_BACKENDS)
    options.extend(BACKEND_CHOICES)
    return options


def _parse_interactive_backend_choice(choice: str) -> InteractiveBackendSelection:
    from stackops.scripts.python.helpers.helpers_utils.read_db_cli_tui_backend import BACKEND_CHOICES

    if choice == "browser":
        return "auto2", "browser", "harlequin"
    if choice == "glow":
        return "auto2", "markdown", "harlequin"
    if choice in BACKEND_CHOICES:
        return "auto2", "database", choice
    return cast(BACKENDS_LOOSE, choice), "auto", "harlequin"


def _choose_backend_interactively(path: str | None) -> InteractiveBackendSelection:
    from stackops.utils.options import choose_from_options

    choice = choose_from_options(
        options=_interactive_backend_options(path=path),
        msg="Select croshell backend",
        multi=False,
        custom_input=False,
        default="ipython",
        tv=True,
    )
    if choice is None:
        typer.echo("Error: no backend selected.", err=True, color=True)
        raise typer.Exit(code=1)
    return _parse_interactive_backend_choice(str(choice))


def croshell(
    path: Annotated[str | None, typer.Argument(help="path of file to read.")] = None,
    project_path: Annotated[str | None, typer.Option("--project", "-p", help="specify uv project to use")] = None,
    uv_with: Annotated[str | None, typer.Option("--uv-with", "-w", help="specify uv with packages to use")] = None,
    backend: Annotated[BACKENDS_LOOSE, typer.Option("--backend", "-b", help="specify the backend to use")] = "ipython",
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="select the backend interactively")] = False,
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
    auto2_mode = "auto"
    auto2_db_backend = "harlequin"
    if interactive:
        backend, auto2_mode, auto2_db_backend = _choose_backend_interactively(path=path)

    from stackops.scripts.python.helpers.helpers_croshell.croshell_impl import croshell as impl
    if auto2_mode != "auto" or auto2_db_backend != "harlequin":
        impl(
            path=path,
            project_path=project_path,
            uv_with=uv_with,
            backend=BACKENDS_MAP[backend],
            profile=profile,
            frozen=frozen,
            auto2_mode=auto2_mode,
            auto2_db_backend=auto2_db_backend,
        )
        return
    impl(
        path=path,
        project_path=project_path,
        uv_with=uv_with,
        backend=BACKENDS_MAP[backend],
        profile=profile,
        frozen=frozen,
    )


def main() -> None:
    typer.run(croshell)


if __name__ == "__main__":
    main()
