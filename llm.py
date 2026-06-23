# /// script
# dependencies = [
#   "stackops",
# ]
# ///

import json
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Annotated, Literal, TypeAlias, cast

import typer
from rich.console import Console


CODEX_SOURCE_ROOT = Path.home() / "dotfiles" / "creds" / "llm" / "codex"
ANTIGRAVITY_SOURCE_ROOT = Path.home() / "dotfiles" / "creds" / "llm" / "agy"
CODEX_DESTINATION = Path.home() / ".codex" / "auth.json"
ANTIGRAVITY_DESTINATION = Path.home() / ".gemini" / "antigravity-cli" / "antigravity-oauth-token"
CODEX_AUTH_FILE_NAME = "auth.json"
ANTIGRAVITY_AUTH_FILE_NAME = "antigravity-oauth-token"

LlmClient: TypeAlias = Literal["codex", "c", "antigravity", "a"]
CanonicalLlmClient: TypeAlias = Literal["codex", "antigravity"]
JsonObject: TypeAlias = dict[str, object]

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()


def _expand_path(path: Path) -> Path:
    return path.expanduser().resolve()


def _list_profile_dirs(source_root: Path) -> list[Path]:
    if not source_root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {source_root}")
    if not source_root.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {source_root}")
    return sorted((path for path in source_root.iterdir() if path.is_dir()), key=lambda path: path.name.casefold())


def _choose_profile(profile_dirs: list[Path], auth_file_name: str) -> Path | None:
    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    profile_by_name = {path.name: path for path in profile_dirs}
    previews = {path.name: f"Profile: {path.name}\nSource directory: {path}\nSource file: {path / auth_file_name}" for path in profile_dirs}
    choice = choose_from_dict_with_preview(previews, extension="txt", multi=False, preview_size_percent=45)
    if choice is None:
        return None
    return profile_by_name[choice]


def _copy_credential(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        shutil.copy2(source, temp_path)
        temp_path.replace(destination)
        destination.chmod(stat.S_IRUSR | stat.S_IWUSR)
    finally:
        temp_path.unlink(missing_ok=True)


def _read_required_json_string(path: Path, keys: tuple[str, ...]) -> str:
    raw_data = cast(object, json.loads(path.read_text(encoding="utf-8")))
    if not isinstance(raw_data, dict):
        raise ValueError(f"Credential file must contain a JSON object: {path}")

    value: object = cast(JsonObject, raw_data)
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f"Credential file is missing required field {'.'.join(keys)}: {path}")
        value = value[key]

    if not isinstance(value, str) or not value:
        raise ValueError(f"Credential field {'.'.join(keys)} must be a non-empty string: {path}")
    return value


def _find_refresh_profile(client: CanonicalLlmClient, profile_dirs: list[Path], auth_file_name: str, active_auth: Path) -> Path:
    match client:
        case "codex":
            identity_keys = ("tokens", "account_id")
        case "antigravity":
            identity_keys = ("token", "refresh_token")

    active_identity = _read_required_json_string(active_auth, identity_keys)
    matching_profiles: list[Path] = []
    for profile_dir in profile_dirs:
        backup_auth = profile_dir / auth_file_name
        if not backup_auth.is_file():
            raise FileNotFoundError(f"Profile has no credential file: {backup_auth}")
        if _read_required_json_string(backup_auth, identity_keys) == active_identity:
            matching_profiles.append(profile_dir)

    if not matching_profiles:
        raise ValueError(f"No {client} backup profile matches the active credential")
    if len(matching_profiles) > 1:
        profile_names = ", ".join(profile.name for profile in matching_profiles)
        raise ValueError(f"Multiple {client} backup profiles match the active credential: {profile_names}")
    return matching_profiles[0]


@app.command()
def main(
    client: Annotated[LlmClient, typer.Argument(help="Profile source: codex (c) or antigravity (a).")],
    destination: Annotated[Path | None, typer.Option("--destination", "-d", help="Override the client-specific authentication destination.")] = None,
    profile: Annotated[
        str | None, typer.Option("--profile", "-p", help="Profile directory name to use without opening the interactive picker.")
    ] = None,
    refresh: Annotated[
        bool, typer.Option("--refresh", "-r", help="Copy the active client credential back to its automatically matched backup profile.")
    ] = False,
) -> None:
    match client:
        case "codex" | "c":
            canonical_client: CanonicalLlmClient = "codex"
            source_root = CODEX_SOURCE_ROOT
            client_name = "Codex"
            client_destination = CODEX_DESTINATION
            auth_file_name = CODEX_AUTH_FILE_NAME
        case "antigravity" | "a":
            canonical_client = "antigravity"
            source_root = ANTIGRAVITY_SOURCE_ROOT
            client_name = "Antigravity"
            client_destination = ANTIGRAVITY_DESTINATION
            auth_file_name = ANTIGRAVITY_AUTH_FILE_NAME

    source_root = _expand_path(source_root)
    destination = _expand_path(client_destination if destination is None else destination)

    try:
        profile_dirs = _list_profile_dirs(source_root)
    except OSError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    if not profile_dirs:
        console.print(f"[red]No profile directories found under {source_root}[/red]")
        raise typer.Exit(code=1)

    if refresh:
        if profile is not None:
            console.print("[red]--profile cannot be used with --refresh because the profile is detected automatically.[/red]")
            raise typer.Exit(code=2)
        if not destination.is_file():
            console.print(f"[red]Active credential file does not exist: {destination}[/red]")
            raise typer.Exit(code=1)

        try:
            selected_dir = _find_refresh_profile(canonical_client, profile_dirs, auth_file_name, destination)
            backup_auth = selected_dir / auth_file_name
            _copy_credential(destination, backup_auth)
        except (OSError, ValueError) as error:
            console.print(f"[red]Failed to refresh backup: {error}[/red]")
            raise typer.Exit(code=1) from error

        console.print(f"[green]Refreshed {client_name} auth backup:[/green] {selected_dir.name}")
        console.print(f"[green]Wrote:[/green] {backup_auth}")
        return

    if profile is None:
        selected_dir = _choose_profile(profile_dirs, auth_file_name)
        if selected_dir is None:
            console.print("[yellow]Cancelled.[/yellow]")
            raise typer.Exit(code=130)
    else:
        matches = {path.name: path for path in profile_dirs}
        selected_dir = matches.get(profile)
        if selected_dir is None:
            console.print(f"[red]Profile not found: {profile}[/red]")
            raise typer.Exit(code=1)

    source_auth = selected_dir / auth_file_name
    if not source_auth.is_file():
        console.print(f"[red]Selected profile has no credential file: {source_auth}[/red]")
        raise typer.Exit(code=1)

    try:
        _copy_credential(source_auth, destination)
    except OSError as error:
        console.print(f"[red]Failed to copy credential: {error}[/red]")
        raise typer.Exit(code=1) from error

    console.print(f"[green]Installed {client_name} auth from profile:[/green] {selected_dir.name}")
    console.print(f"[green]Wrote:[/green] {destination}")


if __name__ == "__main__":
    app()
