"""msearch - Machineconfig search helper."""

import typer
from typing import Annotated


def machineconfig_search(
    path: Annotated[str, typer.Argument(help="The directory/file to search")] = ".",
    search_term: Annotated[str, typer.Argument(help="Initial search term to seed the interactive search")] = "",
    ast: Annotated[bool, typer.Option(..., "--ast", "-a", help="The abstract syntax tree search/ tree sitter search of symbols")] = False,
    symantic: Annotated[bool, typer.Option(..., "--symantic", "-s", help="The symantic search of symbols")] = False,
    extension: Annotated[str | None, typer.Option(..., "--extension", "-E", help="File extension to filter by (e.g., .py, .js)")] = None,
    file: Annotated[bool, typer.Option(..., "--file", "-f", help="File search using fzf")] = False,
    dotfiles: Annotated[bool, typer.Option(..., "--dotfiles", "-D", help="Include dotfiles in search")] = False,
    rga: Annotated[bool, typer.Option(..., "--rga", "-A", help="Use ripgrep-all for searching all (non text files) instead of ripgrep")] = False,
    edit: Annotated[bool, typer.Option(..., "--edit", "-e", help="Open selection in editor (helix)")] = False,
    install_dependencies: Annotated[bool, typer.Option(..., "--install-req", "-i", help="Install required dependencies if missing")] = False,
) -> None:
    """Machineconfig search helper."""
    from machineconfig.scripts.python.helpers.helpers_msearch.msearch_impl import machineconfig_search as impl
    impl(
        path=path,
        search_term=search_term,
        ast=ast,
        symantic=symantic,
        extension=extension,
        file=file,
        dotfiles=dotfiles,
        rga=rga,
        edit=edit,
        install_dependencies=install_dependencies,
    )


def main() -> None:
    app = typer.Typer(add_completion=False, no_args_is_help=True)
    app.command(name="msearch", help=machineconfig_search.__doc__, short_help="machineconfig search helper", no_args_is_help=False)(machineconfig_search)
    app()
