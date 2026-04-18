from pathlib import Path
import os
import platform
import subprocess
from typing import Annotated, Literal

import typer
import stackops.scripts.python.helpers.helpers_devops.themes as theme_assets
from stackops.utils.path_reference import get_path_reference_path


def configure_shell_profile(
    which: Annotated[
        Literal["default", "d", "nushell", "n"],
        typer.Option("--which", "-w", help="Which shell profile to create/configure"),
    ] = "default",
) -> None:
    from stackops.profile.create_shell_profile import create_default_shell_profile, create_nu_shell_profile

    match which:
        case "nushell" | "n":
            create_nu_shell_profile()
            return
        case "default" | "d":
            create_default_shell_profile()
            return
    msg = typer.style("Error: ", fg=typer.colors.RED) + f"Unknown shell profile type: {which}"
    typer.echo(msg)


def pwsh_theme() -> None:
    """🔗 Select powershell prompt theme."""
    from stackops.utils.code import exit_then_run_shell_file

    script_path = get_path_reference_path(
        module=theme_assets,
        path_reference=theme_assets.CHOOSE_PWSH_THEME_PATH_REFERENCE,
    )
    exit_then_run_shell_file(script_path=str(script_path), strict=False)


def starship_theme() -> None:
    """🔗 Select starship prompt theme."""
    if platform.system() == "Windows":
        script_path = get_path_reference_path(
            module=theme_assets,
            path_reference=theme_assets.CHOOSE_STARSHIP_THEME_PS1_PATH_REFERENCE,
        )
        try:
            subprocess.run(["pwsh", "-File", str(script_path)], check=True)
        except FileNotFoundError:
            subprocess.run(["powershell", "-File", str(script_path)], check=True)
        return

    script_path = get_path_reference_path(
        module=theme_assets,
        path_reference=theme_assets.CHOOSE_STARSHIP_THEME_SH_PATH_REFERENCE,
    )
    os.chmod(script_path, 0o755)
    subprocess.run(["bash", str(script_path)], check=True)


def configure_wezterm_theme() -> None:
    """🔗 Select WezTerm theme with interactive live preview."""
    from stackops.scripts.python.helpers.helpers_devops.themes import choose_wezterm_theme

    choose_wezterm_theme.main()


def configure_ghostty_theme() -> None:
    """🔗 Select Ghostty theme with interactive preview."""
    ghostty_config_path = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "ghostty" / "config"
    auto_theme_include = "config-file = ?auto/theme.ghostty"

    existing_lines = ghostty_config_path.read_text(encoding="utf-8").splitlines() if ghostty_config_path.exists() else []
    existing_lines_stripped = [line.strip() for line in existing_lines]
    if auto_theme_include not in existing_lines_stripped:
        ghostty_config_path.parent.mkdir(parents=True, exist_ok=True)
        if existing_lines and existing_lines[-1].strip():
            existing_lines.append("")
        existing_lines.append(auto_theme_include)
        ghostty_config_path.write_text("\n".join(existing_lines) + "\n", encoding="utf-8")

    reload_hint = "cmd+shift+," if platform.system() == "Darwin" else "ctrl+shift+,"
    typer.echo("🎨 Opening Ghostty interactive theme preview. Use arrows/j/k to browse, Enter then w to save.")
    typer.echo(f"💡 After saving, reload Ghostty config with {reload_hint} to apply.")
    subprocess.run(["ghostty", "+list-themes"], check=True)


def configure_windows_terminal_theme() -> None:
    """🔗 Select Windows Terminal color scheme with interactive live preview."""
    if platform.system().lower() != "windows":
        typer.echo("Error: Windows Terminal theme selection is only supported on Windows systems.", err=True)
        raise typer.Exit(code=1)

    script_path = get_path_reference_path(
        module=theme_assets,
        path_reference=theme_assets.CHOOSE_WINDOWS_TERMINAL_THEME_PATH_REFERENCE,
    )
    try:
        subprocess.run(["pwsh", "-File", str(script_path)], check=True)
    except FileNotFoundError:
        subprocess.run(["powershell", "-File", str(script_path)], check=True)


def shell_group(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is not None:
        return
    typer.echo(ctx.get_help())
    raise typer.Exit(code=0)


def get_app() -> typer.Typer:
    shell_app = typer.Typer(help="🐚 <t> Configure your terminal profile.", no_args_is_help=False, add_help_option=True, add_completion=False)
    shell_app.callback(invoke_without_command=True)(shell_group)

    shell_app.command("config-shell", no_args_is_help=False, help="🐚 <s> Create or configure a shell profile.")(configure_shell_profile)
    shell_app.command("s", no_args_is_help=False, help="Create or configure a shell profile.", hidden=True)(configure_shell_profile)
    shell_app.command("starship-theme", no_args_is_help=False, help="⭐ <t> Select starship prompt theme.")(starship_theme)
    shell_app.command("t", no_args_is_help=False, help="Select starship prompt theme.", hidden=True)(starship_theme)
    shell_app.command("pwsh-theme", no_args_is_help=False, help="⚡ <T> Select powershell prompt theme.")(pwsh_theme)
    shell_app.command("T", no_args_is_help=False, help="Select powershell prompt theme.", hidden=True)(pwsh_theme)
    shell_app.command("wezterm-theme", no_args_is_help=False, help="💻 <W> Select WezTerm terminal theme.")(configure_wezterm_theme)
    shell_app.command("W", no_args_is_help=False, help="Select WezTerm terminal theme.", hidden=True)(configure_wezterm_theme)
    shell_app.command("ghostty-theme", no_args_is_help=False, help="👻 <g> Select Ghostty terminal theme.")(configure_ghostty_theme)
    shell_app.command("g", no_args_is_help=False, help="Select Ghostty terminal theme.", hidden=True)(configure_ghostty_theme)
    shell_app.command("windows-terminal-theme", no_args_is_help=False, help="🪟 <x> Select Windows Terminal color scheme.")(
        configure_windows_terminal_theme
    )
    shell_app.command("x", no_args_is_help=False, help="Select Windows Terminal color scheme.", hidden=True)(configure_windows_terminal_theme)
    shell_app.command("wt-theme", no_args_is_help=False, help="Select Windows Terminal color scheme.", hidden=True)(
        configure_windows_terminal_theme
    )

    return shell_app
