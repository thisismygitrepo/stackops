import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Literal, TypeAlias

import stackops.settings.shells.bash_zsh as bash_zsh_shell_assets
import stackops.settings.shells.pwsh as pwsh_shell_assets
from stackops.settings.shells.bash_zsh import INIT_PATH_REFERENCE as BASH_ZSH_INIT_PATH_REFERENCE
from stackops.settings.shells.pwsh import INIT_PATH_REFERENCE as PWSH_INIT_PATH_REFERENCE
from stackops.utils import path_core
from stackops.utils.path_reference import get_path_reference_library_relative_path

LoginShell: TypeAlias = Literal["pwsh", "bash", "zsh"]


@dataclass(frozen=True)
class ShellProfileSource:
    shell_name: LoginShell
    profile_path: Path
    init_script: Path
    source_line: str
    reload_command: str


def build_shell_profile_source(system_name: str, shell_variable: str | None, config_root: Path) -> ShellProfileSource:
    shell_name: LoginShell
    if system_name == "Windows":
        shell_name = "pwsh"
    elif shell_variable is None:
        raise ValueError("""SHELL is not set, so the login shell is unknown. Set SHELL to the path of bash or zsh.""")
    else:
        match Path(shell_variable).name:
            case "bash":
                shell_name = "bash"
            case "zsh":
                shell_name = "zsh"
            case unsupported_shell:
                raise ValueError(f"""Login shell '{unsupported_shell}' (SHELL={shell_variable}) is not supported. Supported shells: bash, zsh.""")

    shell_assets: ModuleType
    match shell_name:
        case "pwsh":
            result = subprocess.run(["pwsh", "-Command", "$PROFILE"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
            if result.returncode != 0 or not result.stdout.strip():
                raise ValueError(f"""Could not get the PowerShell profile path. Return code: {result.returncode}, stdout: {result.stdout}, stderr: {result.stderr}""")
            profile_path = Path(result.stdout.strip())
            shell_assets, init_reference, source_command = pwsh_shell_assets, PWSH_INIT_PATH_REFERENCE, "."
            reload_command = "pwsh $PROFILE"
        case "bash":
            profile_path = Path.home().joinpath(".bashrc")
            shell_assets, init_reference, source_command = bash_zsh_shell_assets, BASH_ZSH_INIT_PATH_REFERENCE, "source"
            reload_command = "source $HOME/.bashrc"
        case "zsh":
            profile_path = Path.home().joinpath(".zshrc")
            shell_assets, init_reference, source_command = bash_zsh_shell_assets, BASH_ZSH_INIT_PATH_REFERENCE, "source"
            reload_command = "source $HOME/.zshrc"

    init_script = config_root.joinpath(get_path_reference_library_relative_path(module=shell_assets, path_reference=init_reference))
    source_line = f"""{source_command} {path_core.collapseuser(init_script, strict=False, placeholder="$HOME")}"""
    return ShellProfileSource(
        shell_name=shell_name, profile_path=profile_path, init_script=init_script, source_line=source_line, reload_command=reload_command
    )
