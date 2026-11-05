"""seek - StackOps search helper."""

from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend


def _resolve_seek_arguments(first_argument: str, search_term: str) -> tuple[str, str]:
    from pathlib import Path

    if search_term != "":
        if first_argument != "." and not Path(first_argument).exists():
            raise typer.BadParameter(
                message=f"Search path does not exist: {first_argument}",
                param_hint="path_or_search_term",
            )
        return first_argument, search_term
    if first_argument == "." or Path(first_argument).exists():
        return first_argument, search_term
    return ".", first_argument


def seek(
    ctx: typer.Context,
    path_or_search_term: Annotated[str, typer.Argument(help="The directory/file to search, or the search term when no matching path exists")] = ".",
    search_term: Annotated[str, typer.Argument(help="Search query; seeds the picker unless --json is used")] = "",
    ast: Annotated[bool, typer.Option(..., "--ast", "-a", help="The abstract syntax tree search/ tree sitter search of symbols")] = False,
    semantic: Annotated[bool, typer.Option(..., "--semantic", "-s", help="Semantic search of text chunks, ranked by meaning rather than keywords")] = False,
    semantic_backend: Annotated[
        SemanticBackend,
        typer.Option(
            ...,
            "--semantic-backend",
            "-b",
            help="Backend for --semantic: ck (local ONNX embeddings, local index), grepai (needs Ollama, local index), qmd (local GGUF models with LLM query expansion, local index, slow), or semtools (stateless, local static embeddings)",
        ),
    ] = "ck",
    extension: Annotated[
        str | None,
        typer.Option(
            ...,
            "--extension",
            "-E",
            help="File extension to filter by (e.g., .py, .js). With --semantic, grepai does not support it and qmd searches .md files unless it is given",
        ),
    ] = None,
    file: Annotated[bool, typer.Option(..., "--file", "-f", help="File search using fzf")] = False,
    dotfiles: Annotated[bool, typer.Option(..., "--dotfiles", "-d", help="Include dotfiles in search")] = False,
    rga: Annotated[bool, typer.Option(..., "--rga", "-A", help="Use ripgrep-all for searching all (non text files) instead of ripgrep")] = False,
    edit: Annotated[bool, typer.Option(..., "--edit", "-e", help="Open selection in editor (helix)")] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", "-j", help="Print a JSON array without prompts or a picker. Text/semantic searches require a query; file/AST searches allow an empty query. No automatic dependency installation."),
    ] = False,
    install_dependencies: Annotated[bool, typer.Option(..., "--install-dependencies", "-i", help="Install missing helper dependencies and exit.")] = False,
    non_interactive: Annotated[bool, typer.Option("--non-interactive", "-N", help="Disable interactive selection; use --json for search results.")] = False,
    max_files: Annotated[
        int,
        typer.Option(
            ...,
            "--max-files",
            "-m",
            help="Maximum files for --semantic search with the semtools backend. Use 0 to disable the limit.",
            min=0,
        ),
    ] = 50,
) -> None:
    """seek across files, text matches, and code symbols."""
    import subprocess

    from stackops.scripts.python.helpers.helpers_seek.seek_impl import seek as impl
    from stackops.utils.cli_utils.interaction import configure_interaction, require_interactive

    configure_interaction(ctx=ctx, non_interactive=non_interactive)
    if not json_output and not install_dependencies:
        require_interactive("Search selection; use --json for noninteractive results")

    path, resolved_search_term = _resolve_seek_arguments(first_argument=path_or_search_term, search_term=search_term)
    if json_output:
        if edit or install_dependencies:
            raise typer.BadParameter("Cannot combine --json with --edit or --install-dependencies.", param_hint="--json")
        if resolved_search_term == "" and (semantic or not (ast or file)):
            raise typer.BadParameter("Provide a search term for text or semantic search with --json.", param_hint="search_term")

    try:
        failure = impl(
            path=path,
            search_term=resolved_search_term,
            ast=ast,
            semantic=semantic,
            semantic_backend=semantic_backend,
            max_files=max_files,
            extension=extension,
            file=file,
            dotfiles=dotfiles,
            rga=rga,
            edit=edit,
            install_dependencies=install_dependencies,
            json_output=json_output,
        )
        if failure is not None:
            typer.echo(f"""Semantic search with {failure.backend} failed during {failure.stage}: {failure.message}""", err=True)
            raise typer.Exit(code=1)
    except OSError as error:
        typer.echo(f"""Search failed: {error}""", err=True)
        raise typer.Exit(code=1) from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr
        if isinstance(detail, bytes):
            detail = detail.decode("utf-8", errors="replace")
        message = f"""Search command failed with exit code {error.returncode}."""
        if detail:
            message += f""" {detail.strip()}"""
        typer.echo(message, err=True)
        raise typer.Exit(code=1) from error


def get_app() -> typer.Typer:
    from stackops.utils.constants import AGENT_SKILL_HINT

    app = typer.Typer(add_completion=False, no_args_is_help=True, context_settings={"help_option_names": ["-h", "--help"]})
    app.command(name="seek", help=seek.__doc__, short_help="stackops search helper", epilog=AGENT_SKILL_HINT, no_args_is_help=False)(seek)
    return app


def main() -> None:
    app = get_app()
    app()
