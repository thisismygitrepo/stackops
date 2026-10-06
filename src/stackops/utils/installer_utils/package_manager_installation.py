import subprocess
from typing import Literal

from rich import print as rich_print
from rich.console import Group
from rich.panel import Panel

from stackops.utils.installer_utils.constants import WINGET_NO_APPLICABLE_UPDATE_CODES


def install_with_package_manager(command: str, requested_version: str | None) -> Literal["installed", "no_applicable_update"]:
    command_parts = command.split()
    package_manager = command_parts[0]
    description = f"""{package_manager} installation"""
    print(f"""📦 Using package manager: {command}""")
    result = subprocess.run(command, shell=True, capture_output=False, text=True, encoding="utf-8", check=False)
    if result.returncode == 0:
        return "installed"

    has_version_argument = any(argument in {"--version", "-v"} or argument.startswith("--version=") for argument in command_parts[2:])
    if (
        tuple(command_parts[:2]) in {("winget", "install"), ("winget", "upgrade")}
        and requested_version is None
        and not has_version_argument
        and result.returncode in WINGET_NO_APPLICABLE_UPDATE_CODES
    ):
        print("😑 WinGet reports no applicable update from the configured sources.")
        return "no_applicable_update"

    group_content = Group(f"""❌ {description} failed\nReturn code: {result.returncode}""")
    rich_print(Panel(group_content, title=description, style="red"))
    raise RuntimeError(f"""{description} failed with return code {result.returncode}""")
