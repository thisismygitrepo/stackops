"""shell"""

from pathlib import Path

import stackops.settings.shells.bash as bash_shell_assets
import stackops.settings.shells.nushell as nushell_assets
import stackops.settings.shells.pwsh as pwsh_shell_assets
import stackops.settings.shells.zsh as zsh_shell_assets
from stackops.settings.shells.bash import INIT_PATH_REFERENCE as BASH_INIT_PATH_REFERENCE
from stackops.settings.shells.nushell import CONFIG_PATH_REFERENCE as NUSHELL_CONFIG_PATH_REFERENCE, ENV_PATH_REFERENCE as NUSHELL_ENV_PATH_REFERENCE
from stackops.settings.shells.pwsh import INIT_PATH_REFERENCE as PWSH_INIT_PATH_REFERENCE
from stackops.settings.shells.zsh import INIT_PATH_REFERENCE as ZSH_INIT_PATH_REFERENCE
import stackops.utils.path_core as path_core
from stackops.utils.path_reference import get_path_reference_library_relative_path


def _to_nushell_join_arguments(path: Path) -> str:
    return " ".join(f'"{part}"' for part in path.parts)


NUSHELL_CONFIG_RELATIVE_PATH = get_path_reference_library_relative_path(
    module=nushell_assets,
    path_reference=NUSHELL_CONFIG_PATH_REFERENCE,
)
NUSHELL_ENV_RELATIVE_PATH = get_path_reference_library_relative_path(
    module=nushell_assets,
    path_reference=NUSHELL_ENV_PATH_REFERENCE,
)
NUSHELL_CONFIG_SOURCE_LINE = (
    f"""source ($nu.home-dir | path join ".config" "stackops" {_to_nushell_join_arguments(NUSHELL_CONFIG_RELATIVE_PATH)})"""
)
NUSHELL_ENV_SOURCE_LINE = (
    f"""source-env ($nu.home-dir | path join ".config" "stackops" {_to_nushell_join_arguments(NUSHELL_ENV_RELATIVE_PATH)})"""
)



def get_shell_profile_path() -> Path:
    import platform
    import subprocess
    from rich.console import Console
    from rich.panel import Panel
    system = platform.system()
    console = Console()
    if system == "Windows":
        result = subprocess.run(["pwsh", "-Command", "$PROFILE"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            profile_path = Path(result.stdout.strip())
        else:
            print(f"Command failed with return code {result.returncode}")
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")
            raise ValueError(f"""Could not get profile path for Windows. Got stdout: {result.stdout}, stderr: {result.stderr}""")
    elif system == "Linux":
        profile_path = Path.home().joinpath(".bashrc")
    elif system == "Darwin":
        profile_path = Path.home().joinpath(".zshrc")
    else:
        raise ValueError(f"""Not implemented for this system {system}""")
    console.print(Panel(f"""🐚 SHELL PROFILE | Working with path: `{profile_path}`""", title="[bold blue]Shell Profile[/bold blue]", border_style="blue"))
    return profile_path


def reload_shell_profile_and_exit() -> None:
    import platform
    if platform.system() == "Windows":
        reload_init_script = "pwsh $PROFILE"
    elif platform.system() == "Darwin":
        reload_init_script = "source $HOME/.zshrc"
    elif platform.system() == "Linux":
        reload_init_script = "source $HOME/.bashrc"
    else:
        reload_init_script = ""
    from stackops.utils.code import exit_then_run_shell_script
    exit_then_run_shell_script(reload_init_script)


def get_nu_shell_profile_path() -> Path:
    import platform
    from rich.console import Console
    from rich.panel import Panel
    system = platform.system()
    console = Console()
    if system == "Windows":
        profile_path = Path.home().joinpath(r"AppData\Roaming\nushell")
    elif system == "Linux":
        profile_path = Path.home().joinpath(".config/nushell")
    elif system == "Darwin":
        profile_path = Path.home().joinpath("Library/Application Support/nushell")
    else:
        raise ValueError(f"""Not implemented for this system {system}""")
    console.print(Panel(f"""🐚 NU SHELL PROFILE | Working with path: `{profile_path}`""", title="[bold cyan]Nu Shell Profile[/bold cyan]", border_style="cyan"))
    return profile_path


def create_default_shell_profile() -> None:
    shell_profile_path = get_shell_profile_path()
    import platform
    import subprocess
    from rich.console import Console
    from rich.panel import Panel
    from stackops.utils.source_of_truth import CONFIG_ROOT
    system = platform.system()
    console = Console()
    if not shell_profile_path.exists():
        console.print(Panel(f"""🆕 PROFILE | Profile does not exist at `{shell_profile_path}`. Creating a new one.""", title="[bold blue]Profile[/bold blue]", border_style="blue"))
        shell_profile_path.parent.mkdir(parents=True, exist_ok=True)
        shell_profile_path.write_text("", encoding="utf-8")
    shell_profile = shell_profile_path.read_text(encoding="utf-8")
    from stackops.profile.create_helper import copy_assets_to_machine
    copy_assets_to_machine("settings")  # init.ps1 or init.sh live here
    copy_assets_to_machine("scripts")  # init scripts are going to reference those scripts.
    shell_name = ""
    if system == "Windows":
        shell_name = "pwsh"
        init_script = Path(CONFIG_ROOT).joinpath(
            get_path_reference_library_relative_path(module=pwsh_shell_assets, path_reference=PWSH_INIT_PATH_REFERENCE)
        )
        source_line = f""". {str(path_core.collapseuser(init_script, placeholder="$HOME"))}"""
    elif system == "Linux":
        shell_name = "bash"
        init_script = Path(CONFIG_ROOT).joinpath(
            get_path_reference_library_relative_path(module=bash_shell_assets, path_reference=BASH_INIT_PATH_REFERENCE)
        )
        source_line = f"""source {str(path_core.collapseuser(init_script, placeholder="$HOME"))}"""
    elif system == "Darwin":
        shell_name = "zsh"
        init_script = Path(CONFIG_ROOT).joinpath(
            get_path_reference_library_relative_path(module=zsh_shell_assets, path_reference=ZSH_INIT_PATH_REFERENCE)
        )
        source_line = f"""source {str(path_core.collapseuser(init_script, placeholder="$HOME"))}"""
    else:
        raise ValueError(f"""Not implemented for this system {system}""")

    was_shell_updated = False
    if source_line in shell_profile:
        console.print(Panel("🔄 PROFILE | Skipping init script sourcing - already present in profile", title="[bold blue]Profile[/bold blue]", border_style="blue"))
    else:
        console.print(Panel("📝 PROFILE | Adding init script sourcing to profile", title="[bold blue]Profile[/bold blue]", border_style="blue"))
        shell_profile += "\n" + source_line + "\n"
        if shell_name == "bash":
            result = subprocess.run(["cat", "/proc/version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if result.returncode == 0 and result.stdout:
                version_info = result.stdout.lower()
                is_wsl = "microsoft" in version_info or "wsl" in version_info
                if is_wsl:
                    shell_profile += "\ncd $HOME"
                    console.print("📌 WSL detected - adding 'cd $HOME' to profile to avoid Windows filesystem")
                    # Sync shell history between Windows and WSL
                    # https://www.hanselman.com/blog/sharing-powershell-history-between-windows-and-wsl
                    shell_profile += """
# Sync shell history between Windows and WSL
export PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND$'\\n'}history -a; history -c; history -r"
"""
        was_shell_updated = True
    if was_shell_updated:
        shell_profile_path.parent.mkdir(parents=True, exist_ok=True)
        shell_profile_path.write_text(shell_profile, encoding="utf-8")
        console.print(Panel("✅ Profile updated successfully", title="[bold blue]Profile[/bold blue]", border_style="blue"))


def create_nu_shell_profile() -> None:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    config_dir = get_nu_shell_profile_path()
    config_file = config_dir.joinpath("config.nu")
    env_file = config_dir.joinpath("env.nu")
    if not config_dir.exists():
        console.print(Panel(f"""🆕 NU SHELL CONFIG | Config directory does not exist at `{config_dir}`. Creating a new one.""", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))
        config_dir.mkdir(parents=True, exist_ok=True)
    from stackops.profile.create_helper import copy_assets_to_machine
    copy_assets_to_machine("settings")
    copy_assets_to_machine("scripts")
    desired_config = NUSHELL_CONFIG_SOURCE_LINE + "\n"
    desired_env = NUSHELL_ENV_SOURCE_LINE + "\n"
    current_config = config_file.read_text(encoding="utf-8") if config_file.exists() else None
    current_env = env_file.read_text(encoding="utf-8") if env_file.exists() else None
    if current_config == desired_config:
        console.print(Panel("🔄 NU SHELL CONFIG | config.nu already matches the managed wrapper.", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))
    else:
        console.print(Panel(f"""📝 NU SHELL CONFIG | Writing managed config.nu wrapper to `{config_file}`.""", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))
        config_file.write_text(desired_config, encoding="utf-8")
        console.print(Panel("✅ Nu shell config updated successfully", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))
    if current_env == desired_env:
        console.print(Panel("🔄 NU SHELL CONFIG | env.nu already matches the managed wrapper.", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))
    else:
        console.print(Panel(f"""📝 NU SHELL CONFIG | Writing managed env.nu wrapper to `{env_file}`.""", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))
        env_file.write_text(desired_env, encoding="utf-8")
        console.print(Panel("✅ Nu shell env updated successfully", title="[bold cyan]Nu Shell Config[/bold cyan]", border_style="cyan"))


if __name__ == "__main__":
    pass
