from pathlib import Path

import typer

from stackops.scripts.python.helpers.helpers_devops.script_sources import get_script_locations
from stackops.scripts.python.helpers.helpers_search.script_help import SCRIPT_SOURCE


IGNORED_SCRIPT_MATCH_DIR_NAMES: frozenset[str] = frozenset({
    "__pycache__",
    ".git",
    ".ipynb_checkpoints",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "node_modules",
})


def _get_supported_script_suffixes(name: str) -> tuple[str, ...]:
    import platform

    if "." in name:
        return (Path(name).suffix,)
    match platform.system():
        case "Windows":
            return (".py", ".bat", ".cmd", ".ps1")
        case "Darwin" | "Linux":
            return ("", ".py", ".sh")
        case _:
            return (".py",)


def _is_supported_script_match(file_path: Path, root: Path, supported_suffixes: frozenset[str]) -> bool:
    if not file_path.is_file() or file_path.name == "__init__.py":
        return False
    relative_parts = file_path.relative_to(root).parts
    if any(part in IGNORED_SCRIPT_MATCH_DIR_NAMES for part in relative_parts[:-1]):
        return False
    return file_path.suffix in supported_suffixes


def _fetch_dynamic_script(name: str) -> Path:
    import requests

    if not name:
        raise typer.BadParameter("Provide a script name when using --source dynamic.")
    resolved_names = [name] if "." in name else [f"""{name}{suffix}""" for suffix in (".py", ".sh", "", ".ps1", ".bat", ".cmd")]
    for resolved_name in resolved_names:
        url = f"""https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/src/stackops/jobs/scripts_dynamic/{resolved_name}"""
        typer.echo(f"""Fetching temporary script from {url} ...""", err=True)
        response = requests.get(url, timeout=30)
        if response.status_code == 404:
            continue
        response.raise_for_status()
        target_file = Path.home().joinpath("tmp_results", "tmp_scripts", "python", resolved_name)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(response.text, encoding="utf-8")
        return target_file
    typer.echo(f"""❌ ERROR: Could not find dynamic script '{name}'.""", err=True)
    raise typer.Exit(code=1)


def resolve_script(*, ctx: typer.Context, name: str, source: SCRIPT_SOURCE, interactive: bool) -> Path:
    if not interactive and not name:
        typer.echo("❌ ERROR: You must provide a script name or use --interactive to select a script.", err=True)
        raise typer.Exit(code=1)
    if source in {"dynamic", "d"}:
        return _fetch_dynamic_script(name=name)

    target_file: Path | None = None
    if Path(name).is_file():
        direct_target_file = Path(name).resolve()
        if direct_target_file.suffix not in {".py", ".sh", ".ps1", ".bat", ".cmd", ""}:
            typer.echo(f"""❌ ERROR: File '{name}' is not a recognized script type.""", err=True)
            raise typer.Exit(code=1)
        target_file = direct_target_file

    roots = [location for location in get_script_locations(source=source).values() if isinstance(location, Path)]
    if target_file is not None:
        return target_file
    suffixes = _get_supported_script_suffixes(name=name)
    exact_names = [name] if "." in name else [f"""{name}{suffix}""" for suffix in suffixes]
    supported_suffixes = frozenset(suffixes)
    potential_matches: list[Path] = []
    seen_matches: set[Path] = set()
    for root in roots:
        for exact_name in exact_names:
            exact_path = root.joinpath(exact_name)
            if _is_supported_script_match(file_path=exact_path, root=root, supported_suffixes=supported_suffixes):
                return exact_path
        for file_path in sorted(root.rglob(f"""*{name}*""")):
            if not _is_supported_script_match(file_path=file_path, root=root, supported_suffixes=supported_suffixes):
                continue
            if file_path not in seen_matches:
                potential_matches.append(file_path)
                seen_matches.add(file_path)

    if len(potential_matches) == 1:
        return potential_matches[0]
    if not potential_matches:
        typer.echo(ctx.get_help(), err=True)
        typer.echo(err=True)
        typer.echo(typer.style(f"""❌ ERROR: Could not find script '{name}'.""", fg=typer.colors.RED, bold=True), err=True)
        typer.echo("Searched in:", err=True)
        for root in roots:
            typer.echo(f"""  - {root}""", err=True)
        raise typer.Exit(code=1)

    typer.echo(typer.style(f"""❌ ERROR: Found {len(potential_matches)} scripts matching '{name}'.""", fg=typer.colors.RED, bold=True), err=True)
    for candidate in potential_matches:
        typer.echo(f"""  - {candidate}""", err=True)
    if not interactive:
        typer.echo("Re-run with --interactive to choose one explicitly.", err=True)
        raise typer.Exit(code=1)
    from stackops.utils.options_utils.options import choose_from_options

    chosen_file = choose_from_options([str(path) for path in potential_matches], multi=False, msg="Select a script:", tv=True, preview="bat")
    if chosen_file is None:
        typer.echo(typer.style("❌ Selection cancelled.", fg=typer.colors.YELLOW), err=True)
        raise typer.Exit(code=1)
    return Path(chosen_file)
