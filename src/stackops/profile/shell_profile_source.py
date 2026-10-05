from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import stackops.settings.shells.bash as bash_shell_assets
import stackops.settings.shells.pwsh as pwsh_shell_assets
import stackops.settings.shells.zsh as zsh_shell_assets
import stackops.utils.path_core as path_core
from stackops.settings.shells.bash import INIT_PATH_REFERENCE as BASH_INIT_PATH_REFERENCE
from stackops.settings.shells.pwsh import INIT_PATH_REFERENCE as PWSH_INIT_PATH_REFERENCE
from stackops.settings.shells.zsh import INIT_PATH_REFERENCE as ZSH_INIT_PATH_REFERENCE
from stackops.utils.path_reference import get_path_reference_library_relative_path


@dataclass(frozen=True)
class ShellProfileSource:
    shell_name: Literal["pwsh", "bash", "zsh"]
    init_script: Path
    source_line: str


def build_shell_profile_source(system_name: str, config_root: Path) -> ShellProfileSource:
    shell_name: Literal["pwsh", "bash", "zsh"]
    match system_name:
        case "Windows":
            shell_name = "pwsh"
            shell_assets, init_reference, source_command = pwsh_shell_assets, PWSH_INIT_PATH_REFERENCE, "."
        case "Linux":
            shell_name = "bash"
            shell_assets, init_reference, source_command = bash_shell_assets, BASH_INIT_PATH_REFERENCE, "source"
        case "Darwin":
            shell_name = "zsh"
            shell_assets, init_reference, source_command = zsh_shell_assets, ZSH_INIT_PATH_REFERENCE, "source"
        case _:
            raise ValueError(f"""Not implemented for this system {system_name}""")

    init_script = config_root.joinpath(get_path_reference_library_relative_path(module=shell_assets, path_reference=init_reference))
    source_line = f"""{source_command} {path_core.collapseuser(init_script, strict=False, placeholder="$HOME")}"""
    return ShellProfileSource(shell_name=shell_name, init_script=init_script, source_line=source_line)
