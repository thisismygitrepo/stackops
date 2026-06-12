from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

import typer

TmuxInstallLocation = Literal["xdg", "home"]
TmuxPreset = Literal["stackops", "catppuccin-mocha", "gruvbox-dark"]
STACKOPS_MANAGED_HEADER = "# StackOps tmux-style managed options"
TMUX_PRESET_COLOURS: dict[TmuxPreset, tuple[str, ...]] = {
    "stackops": ("#080808", "#303030", "#8a8a8a", "#00afff", "#ffff00", "#080808", "#e4e4e4", "#080808", "#ffff00", "#ff00af", "#5fff00", "#8a8a8a", "#e4e4e4", "#080808", "#080808", "#d70000", "#e4e4e4"),
    "catppuccin-mocha": ("#11111b", "#313244", "#6c7086", "#89b4fa", "#f9e2af", "#11111b", "#cdd6f4", "#11111b", "#a6e3a1", "#f5c2e7", "#94e2d5", "#6c7086", "#cdd6f4", "#11111b", "#11111b", "#f38ba8", "#cdd6f4"),
    "gruvbox-dark": ("#1d2021", "#3c3836", "#928374", "#83a598", "#fabd2f", "#1d2021", "#ebdbb2", "#1d2021", "#b8bb26", "#d3869b", "#8ec07c", "#928374", "#ebdbb2", "#1d2021", "#1d2021", "#fb4934", "#ebdbb2"),
}


@dataclass(frozen=True)
class TmuxStylePaths:
    location: TmuxInstallLocation
    framework_dir: Path
    config_path: Path
    local_config_path: Path


def _reject_native_windows() -> None:
    import platform
    if platform.system() == "Windows":
        typer.echo("Error: tmux styling is supported on Unix-like systems and WSL/Cygwin, not native Windows.", err=True)
        raise typer.Exit(code=1)


def _xdg_config_home() -> Path:
    import os
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser()


def _paths(location: TmuxInstallLocation) -> TmuxStylePaths:
    if location == "xdg":
        d = _xdg_config_home() / "tmux"
        return TmuxStylePaths(location, d / "oh-my-tmux", d / "tmux.conf", d / "tmux.conf.local")
    h = Path.home()
    return TmuxStylePaths(location, h / ".tmux", h / ".tmux.conf", h / ".tmux.conf.local")


def _stackops_local_config_text() -> str:
    import stackops.settings.tmux as tmux_assets
    from stackops.utils.path_reference import get_path_reference_path
    return get_path_reference_path(module=tmux_assets, path_reference=tmux_assets.TMUX_CONF_LOCAL_PATH_REFERENCE).read_text(encoding="utf-8")


def _path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _backup_path(path: Path) -> Path:
    import shutil
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    result = path.with_name(f"{path.name}.stackops-bak-{ts}")
    c = 1
    while _path_exists(result):
        result = path.with_name(f"{path.name}.stackops-bak-{ts}.{c}")
        c += 1
    shutil.move(str(path), str(result))
    return result


def _write_text(path: Path, content: str, *, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if _path_exists(path):
        if path.is_file() and not path.is_symlink() and path.read_text(encoding="utf-8") == content:
            typer.echo(f"Already current: {path}")
            return
        if not force:
            typer.echo(f"Error: {path} already exists. Rerun with --force to replace it.", err=True)
            raise typer.Exit(code=1)
        typer.echo(f"Backed up {path} to {_backup_path(path)}")
    path.write_text(content, encoding="utf-8")
    typer.echo(f"Wrote {path}")


def _write_stackops_local(paths: TmuxStylePaths, *, force: bool) -> None:
    _write_text(paths.local_config_path, _stackops_local_config_text(), force=force)


def _run_checked(command: list[str], *, cwd: Path | None = None) -> None:
    import subprocess
    try:
        subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)
    except FileNotFoundError as exc:
        typer.echo(f"Error: required command not found: {command[0]}", err=True)
        raise typer.Exit(code=1) from exc
    except subprocess.CalledProcessError as exc:
        raise typer.Exit(code=exc.returncode) from exc


def install_oh_my_tmux(
    update: Annotated[bool, typer.Option("--update", "-u", help="Fast-forward an existing Oh My Tmux checkout.")] = False,
    apply_stackops_local_config: Annotated[bool, typer.Option("--apply-stackops-local", "-a", help="Replace ~/.tmux.conf.local with the StackOps Oh My Tmux local config after installation.")] = False,
    force_local: Annotated[bool, typer.Option("--force-local", "-f", help="Back up and replace an existing ~/.tmux.conf.local.")] = False,
) -> None:
    """Install Oh My Tmux through the shared StackOps installer."""
    _reject_native_windows()
    from stackops.utils.installer_utils.installer_cli import main_installer_cli
    main_installer_cli(which="oh-my-tmux", group=False, interactive=False, explore=False, update=update, version=None)
    if apply_stackops_local_config:
        _write_stackops_local(_paths("home"), force=force_local)
    typer.echo("Done. Restart tmux or run `devops config terminal tmux-style reload --location home`.")


def apply_stackops_local(
    location: Annotated[TmuxInstallLocation, typer.Option("--location", "-l", help="tmux config location to update.")] = "home",
    force: Annotated[bool, typer.Option("--force", "-f", help="Back up and replace an existing local config.")] = False,
) -> None:
    """Copy StackOps' Oh My Tmux local customization file."""
    _reject_native_windows()
    _write_stackops_local(_paths(location), force=force)


def _read_local_lines(path: Path) -> list[str]:
    if not path.exists():
        typer.echo(f"Error: local tmux config does not exist at {path}. Run apply-stackops-local or install-oh-my-tmux first.", err=True)
        raise typer.Exit(code=1)
    return path.read_text(encoding="utf-8").splitlines()


def _set_tmux_conf_assignment(path: Path, name: str, value: str, *, raw: bool) -> None:
    import re
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name) or not name.startswith("tmux_conf_"):
        typer.echo("Error: option name must be an Oh My Tmux variable starting with tmux_conf_.", err=True)
        raise typer.Exit(code=1)
    if raw:
        formatted = value
    else:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$")
        formatted = f'"{escaped}"'
    assignment = f"{name}={formatted}"
    lines = _read_local_lines(path)
    target_re = re.compile(rf"^\s*{re.escape(name)}=")
    next_lines: list[str] = []
    replaced = False
    for line in lines:
        if target_re.match(line) and not replaced:
            next_lines.append(assignment)
            replaced = True
        else:
            next_lines.append(line)
    if not replaced:
        if next_lines and next_lines[-1].strip():
            next_lines.append("")
        if STACKOPS_MANAGED_HEADER not in next_lines:
            next_lines.append(STACKOPS_MANAGED_HEADER)
        next_lines.append(assignment)
    path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
    typer.echo(f"Set {name} in {path}")


def set_option(
    name: Annotated[str, typer.Argument(help="Oh My Tmux variable name, for example tmux_conf_theme_colour_4.")],
    value: Annotated[str, typer.Argument(help="Value to write into the local config.")],
    location: Annotated[TmuxInstallLocation, typer.Option("--location", "-l", help="tmux config location to update.")] = "home",
    raw: Annotated[bool, typer.Option("--raw", "-R", help="Write VALUE without shell quoting.")] = False,
    reload_config: Annotated[bool, typer.Option("--reload", "-r", help="Reload tmux after updating the local config.")] = False,
) -> None:
    """Set one Oh My Tmux variable in the local customization file."""
    _reject_native_windows()
    paths = _paths(location)
    _set_tmux_conf_assignment(paths.local_config_path, name, value, raw=raw)
    if reload_config:
        reload_tmux(location=location)


def preset(
    which: Annotated[TmuxPreset, typer.Argument(help="Oh My Tmux color preset to apply.")],
    location: Annotated[TmuxInstallLocation, typer.Option("--location", "-l", help="tmux config location to update.")] = "home",
    reload_config: Annotated[bool, typer.Option("--reload", "-r", help="Reload tmux after updating the local config.")] = False,
) -> None:
    """Apply a color preset using Oh My Tmux theme variables."""
    _reject_native_windows()
    paths = _paths(location)
    for index, colour in enumerate(TMUX_PRESET_COLOURS[which], start=1):
        _set_tmux_conf_assignment(paths.local_config_path, f"tmux_conf_theme_colour_{index}", colour, raw=False)
    typer.echo(f"Applied {which} preset to {paths.local_config_path}")
    if reload_config:
        reload_tmux(location=location)


def reload_tmux(
    location: Annotated[TmuxInstallLocation, typer.Option("--location", "-l", help="tmux config location to reload.")] = "home",
) -> None:
    """Reload tmux from the Oh My Tmux main config."""
    _reject_native_windows()
    paths = _paths(location)
    if not paths.config_path.exists():
        typer.echo(f"Error: tmux config does not exist at {paths.config_path}", err=True)
        raise typer.Exit(code=1)
    _run_checked(["tmux", "source-file", str(paths.config_path)])
    typer.echo(f"Reloaded {paths.config_path}")


def status(
    location: Annotated[TmuxInstallLocation, typer.Option("--location", "-l", help="tmux config location to inspect.")] = "home",
) -> None:
    """Show tmux styling paths and install status."""
    paths = _paths(location)
    symlink_target = paths.config_path.resolve(strict=False) if paths.config_path.is_symlink() else None
    typer.echo(f"location: {paths.location}")
    typer.echo(f"framework: {paths.framework_dir} ({'present' if paths.framework_dir.exists() else 'missing'})")
    if symlink_target is None:
        typer.echo(f"config: {paths.config_path} ({'present' if paths.config_path.exists() else 'missing'})")
    else:
        typer.echo(f"config: {paths.config_path} -> {symlink_target}")
    typer.echo(f"local: {paths.local_config_path} ({'present' if paths.local_config_path.exists() else 'missing'})")


def tmux_style_group(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    typer.echo(ctx.get_help())
    raise typer.Exit(code=0)


def get_app() -> typer.Typer:
    tmux_app = typer.Typer(help="Style tmux through the Oh My Tmux framework.", no_args_is_help=False, add_help_option=True, add_completion=False)
    tmux_app.callback(invoke_without_command=True)(tmux_style_group)
    for name, short, help_text, fn in (
        ("install-oh-my-tmux", "i", "Install Oh My Tmux and link tmux to it.", install_oh_my_tmux),
        ("apply-stackops-local", "l", "Copy the StackOps Oh My Tmux local config.", apply_stackops_local),
        ("preset", "p", "Apply an Oh My Tmux color preset.", preset),
        ("set-option", "s", "Set an Oh My Tmux tmux_conf_* option.", set_option),
        ("reload", "r", "Reload tmux config.", reload_tmux),
    ):
        tmux_app.command(name, no_args_is_help=False, help=help_text)(fn)  # type: ignore[arg-type]
        tmux_app.command(short, no_args_is_help=False, help=help_text, hidden=True)(fn)  # type: ignore[arg-type]
    tmux_app.command("status", no_args_is_help=False, help="Show tmux styling status.")(status)
    return tmux_app
