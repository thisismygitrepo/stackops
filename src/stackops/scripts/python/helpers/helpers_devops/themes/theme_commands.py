import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal

import typer

from stackops.utils.cli_utils.interaction import require_interactive


def validate_theme_request(*, theme: str | None, list_names: bool, json_output: bool) -> None:
    if theme is not None and list_names:
        raise typer.BadParameter("--theme cannot be combined with --list")
    if theme is not None and not theme.strip():
        raise typer.BadParameter("--theme must not be blank")
    if json_output and theme is None and not list_names:
        raise typer.BadParameter("--json requires --theme or --list")
    if theme is None and not list_names:
        require_interactive("Theme preview; supply --theme NAME or --list --json")


def configure_named_theme(*, target: Literal["starship", "wezterm", "ghostty"], theme: str | None, list_names: bool, json_output: bool) -> bool:
    validate_theme_request(theme=theme, list_names=list_names, json_output=json_output)
    if theme is None and not list_names:
        return False
    try:
        if target == "wezterm":
            from stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme import schemes_list

            names = tuple(schemes_list)
        else:
            command = ["starship", "preset", "--list"] if target == "starship" else ["ghostty", "+list-themes", "--plain"]
            result = subprocess.run(command, check=True, capture_output=True, text=True)
            names = tuple(dict.fromkeys(
                re.sub(r"\s+\([^)]*\)$", "", line.strip()) if target == "ghostty" else line.strip()
                for line in result.stdout.splitlines() if line.strip()
            ))
        if not names:
            raise ValueError(f"No {target} themes are available")
        if list_names:
            typer.echo(json.dumps({"target": target, "themes": names}) if json_output else "\n".join(names))
            return True
        if theme is None or theme not in names:
            raise ValueError(f"Unknown {target} theme {theme!r}. Use --list to inspect exact names.")
        config_root = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()
        if target == "starship":
            result = subprocess.run(["starship", "preset", theme], check=True, capture_output=True, text=True)
            path = Path(os.environ.get("STARSHIP_CONFIG", str(config_root / "starship.toml"))).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result.stdout, encoding="utf-8")
            paths = [path]
        elif target == "wezterm":
            from stackops.scripts.python.helpers.helpers_devops.themes.choose_wezterm_theme import set_theme

            paths = [set_theme(theme)]
        else:
            from stackops.settings.shells.ghostty import CONFIG_PATH_REFERENCE

            path = config_root / "ghostty" / CONFIG_PATH_REFERENCE
            lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
            include = "config-file = ?auto/theme.ghostty"
            lines = [line for line in lines if line.strip() != include]
            lines.append(include)
            theme_path = path.parent / "auto" / "theme.ghostty"
            theme_path.parent.mkdir(parents=True, exist_ok=True)
            theme_path.write_text(f"theme = {theme}\n", encoding="utf-8")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            paths = [path, theme_path]
        receipt = {"target": target, "theme": theme, "paths": [str(path) for path in paths], "applied": True}
        typer.echo(json.dumps(receipt) if json_output else f"Applied {target} theme: {theme}")
        return True
    except subprocess.CalledProcessError as error:
        typer.echo(error.stderr.strip() if error.stderr else str(error), err=True)
        raise typer.Exit(code=error.returncode) from error
    except (OSError, ValueError) as error:
        raise typer.BadParameter(str(error)) from error


def run_powershell_theme(*, script_path: Path, theme: str | None, list_names: bool, json_output: bool, allow_windows_powershell: bool) -> None:
    validate_theme_request(theme=theme, list_names=list_names, json_output=json_output)
    shell = shutil.which("pwsh")
    if shell is None and allow_windows_powershell:
        shell = shutil.which("powershell")
    if shell is None:
        raise typer.BadParameter("PowerShell is required for this theme command")
    command = [shell, "-NoProfile", "-File", str(script_path)]
    if theme is not None:
        command.extend(["-Theme", theme])
    if list_names:
        command.append("-List")
    if json_output:
        command.append("-Json")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)
