from pathlib import Path
from shlex import quote
from typing import Annotated

import typer


def cleanup(
    repo: Annotated[str | None, typer.Argument(help="📁 Directory containing repo(s).")] = None,
    recursive: Annotated[bool, typer.Option("--recursive", "-r", help="🔍 Recurse into nested repositories.")] = False,
) -> None:
    if repo is None:
        repo = Path.cwd().as_posix()

    arg_path = Path(repo).expanduser().absolute().resolve()
    if not arg_path.exists():
        typer.echo(f"❌ Path does not exist: {arg_path}")
        raise typer.Exit(code=1)
    if not arg_path.is_dir():
        typer.echo(f"❌ Path is not a directory: {arg_path}")
        raise typer.Exit(code=1)

    from git import InvalidGitRepositoryError, Repo

    if not recursive:
        try:
            repo_obj = Repo(str(arg_path), search_parent_directories=False)
        except InvalidGitRepositoryError:
            typer.echo(f"❌ {arg_path} is not a git repository. Use -r flag for recursive cleanup.")
            raise typer.Exit(code=1)
        if repo_obj.working_tree_dir is None:
            typer.echo(f"❌ {arg_path} is inside a bare git repository. Pass a working tree root and retry.")
            raise typer.Exit(code=1)
        repo_root = Path(repo_obj.working_tree_dir).resolve()
        if arg_path != repo_root:
            typer.echo(f"❌ {arg_path} is not a git working tree root. Pass the repository root or use -r for recursive cleanup.")
            raise typer.Exit(code=1)
        repos_to_clean = [repo_root]
    else:
        git_dirs = list(arg_path.rglob(".git"))
        repos_to_clean = [git_dir.parent for git_dir in git_dirs if git_dir.is_dir() or git_dir.is_file()]
        if not repos_to_clean:
            typer.echo(f"❌ No git repositories found under {arg_path}")
            raise typer.Exit(code=1)

    for repo_path in repos_to_clean:
        typer.echo(f"🧹 Cleaning {repo_path}")
        script = rf"""
cd {quote(repo_path.as_posix())}
uv run --no-project --with cleanpy cleanpy .
"""
        from stackops.utils.code import run_shell_script

        result = run_shell_script(script, display_script=True, clean_env=False)
        if result.returncode != 0:
            raise typer.Exit(code=result.returncode)


def config_linters(
    directory: Annotated[str, typer.Argument(help="📁 Git repository directory to configure.")] = ".",
    linter: Annotated[str | None, typer.Option("--linter", "-t", help="Linter to configure: ruff, mypy, pylint, flake8, ty.")] = None,
) -> None:
    target_dir = Path(directory).expanduser().absolute().resolve()
    if not target_dir.exists():
        typer.echo(f"❌ Path does not exist: {target_dir}")
        raise typer.Exit(code=1)
    if not target_dir.is_dir():
        typer.echo(f"❌ Path is not a directory: {target_dir}")
        raise typer.Exit(code=1)

    from git import InvalidGitRepositoryError, Repo

    try:
        repo = Repo(str(target_dir), search_parent_directories=True)
    except InvalidGitRepositoryError as exc:
        typer.echo(f"❌ {target_dir} is not within a git repository. Pass a path inside a git repo and retry.")
        raise typer.Exit(code=1) from exc

    if repo.working_tree_dir is None:
        typer.echo(f"❌ {target_dir} is inside a bare git repository. Pass a working tree path and retry.")
        raise typer.Exit(code=1)

    repo_root = Path(repo.working_tree_dir).resolve()
    templates_dir = Path(__file__).resolve().parents[4].joinpath("settings", "linters")
    if not templates_dir.exists():
        typer.echo(f"❌ Linter template directory not found: {templates_dir}")
        raise typer.Exit(code=1)

    linter_to_file: dict[str, str] = {"flake8": ".flake8", "mypy": ".mypy.ini", "pylint": ".pylintrc", "ruff": ".ruff.toml", "ty": "ty.toml"}
    available_linters: list[str] = sorted(linter_to_file.keys())

    if linter is not None and linter not in linter_to_file:
        typer.echo(f"❌ Unsupported linter '{linter}'. Choose one of: {', '.join(available_linters)}")
        raise typer.Exit(code=1)

    selected_linters = available_linters if linter is None else [linter]
    for selected_linter in selected_linters:
        file_name = linter_to_file[selected_linter]
        source = templates_dir.joinpath(file_name)
        if not source.exists():
            typer.echo(f"❌ Linter template not found: {source}")
            raise typer.Exit(code=1)
        template_content = source.read_text(encoding="utf-8")
        destination = repo_root.joinpath(file_name)
        if destination.exists():
            if not destination.is_file():
                typer.echo(f"❌ Refusing to overwrite non-file path: {destination}")
                raise typer.Exit(code=1)
            if destination.read_text(encoding="utf-8") == template_content:
                typer.echo(f"ℹ️ {file_name} already matches the template in {repo_root}")
                continue
            typer.echo(f"❌ Refusing to overwrite existing {file_name} in {repo_root}. Remove it or update it manually.")
            raise typer.Exit(code=1)
        destination.write_text(template_content, encoding="utf-8")
        typer.echo(f"✅ Added {file_name} to {repo_root}")
