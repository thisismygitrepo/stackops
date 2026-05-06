"""seek - StackOps search helper."""

from pathlib import Path
from typing import Annotated

import typer


def _resolve_seek_arguments(first_argument: str, search_term: str) -> tuple[str, str]:
    if search_term != "":
        return first_argument, search_term
    if first_argument == "." or Path(first_argument).exists():
        return first_argument, search_term
    return ".", first_argument


def seek(
    path_or_search_term: Annotated[str, typer.Argument(help="The directory/file to search, or the search term when no matching path exists")] = ".",
    search_term: Annotated[str, typer.Argument(help="Initial search term to seed the interactive search")] = "",
    ast: Annotated[bool, typer.Option(..., "--ast", "-a", help="The abstract syntax tree search/ tree sitter search of symbols")] = False,
    symantic: Annotated[bool, typer.Option(..., "--symantic", "-s", help="The symantic search of symbols")] = False,
    extension: Annotated[str | None, typer.Option(..., "--extension", "-E", help="File extension to filter by (e.g., .py, .js)")] = None,
    file: Annotated[bool, typer.Option(..., "--file", "-f", help="File search using fzf")] = False,
    dotfiles: Annotated[bool, typer.Option(..., "--dotfiles", "-d", help="Include dotfiles in search")] = False,
    rga: Annotated[bool, typer.Option(..., "--rga", "-A", help="Use ripgrep-all for searching all (non text files) instead of ripgrep")] = False,
    edit: Annotated[bool, typer.Option(..., "--edit", "-e", help="Open selection in editor (helix)")] = False,
    install_dependencies: Annotated[bool, typer.Option(..., "--install-req", "-i", help="Install required dependencies if missing")] = False,
) -> None:
    """seek across files, text matches, and code symbols."""
    from stackops.scripts.python.helpers.helpers_seek.seek_impl import seek as impl

    path, resolved_search_term = _resolve_seek_arguments(first_argument=path_or_search_term, search_term=search_term)

    impl(
        path=path,
        search_term=resolved_search_term,
        ast=ast,
        symantic=symantic,
        extension=extension,
        file=file,
        dotfiles=dotfiles,
        rga=rga,
        edit=edit,
        install_dependencies=install_dependencies,
    )


def get_app() -> typer.Typer:
    app = typer.Typer(add_completion=False, no_args_is_help=True)
    app.command(name="seek", help=seek.__doc__, short_help="stackops search helper", no_args_is_help=False)(seek)
    return app


def main() -> None:
    app = get_app()
    app()
