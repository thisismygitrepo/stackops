import os
import platform
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Literal

import requests
from rich import print as rich_print
from rich.console import Group
from rich.panel import Panel

from stackops.utils.installer_utils.constants import WINGET_NO_APPLICABLE_UPDATE_CODES


_POWERSHELL_DOWNLOAD_AND_EXECUTE_PATTERN = re.compile(
    r"""^\s*(?:powershell(?:\.exe)?\s+(?:.*?\s)?-(?:c|command)\s+"?)?\s*irm\s+(?P<url>https?://\S+)\s*\|\s*iex\s*"?\s*$""", re.IGNORECASE
)


def _extract_powershell_script_url(command: str) -> str | None:
    match = _POWERSHELL_DOWNLOAD_AND_EXECUTE_PATTERN.match(command)
    return None if match is None else match.group("url")


# Why `irm <url> | iex` installers are not run as-is on Windows:
# 1. Microsoft Defender flags the command line `cmd.exe /c powershell -c "irm <url> | iex"` (what `shell=True` spawns) as
#    Trojan:Win32/Commando.A!ml and blocks process creation, which surfaces in Python as `PermissionError: [WinError 5] Access is denied`.
#    Downloading the script in Python and running it with `-File` avoids the flagged download-and-execute command line.
# 2. Windows PowerShell 5.1 launched from Python inherits pwsh 7's PSModulePath, loads the wrong core modules and loses cmdlets
#    such as Get-FileHash. pwsh resets this when it launches powershell.exe itself; Python does not, so PSModulePath is dropped here.
def _run_downloaded_powershell_script(script_url: str) -> subprocess.CompletedProcess[str]:
    print(f"""⬇️  Downloading PowerShell installer script: {script_url}""")
    response = requests.get(script_url, timeout=60)
    response.raise_for_status()
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ps1", encoding="utf-8-sig", delete=False) as script_file:
        script_file.write(response.text)
        script_path = Path(script_file.name)
    child_env = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    try:
        return subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
            capture_output=False, text=True, encoding="utf-8", env=child_env, check=False,
        )
    finally:
        script_path.unlink(missing_ok=True)


def install_with_package_manager(command: str, requested_version: str | None) -> Literal["installed", "no_applicable_update"]:
    command_parts = command.split()
    package_manager = command_parts[0]
    description = f"""{package_manager} installation"""
    print(f"""📦 Using package manager: {command}""")
    powershell_script_url = _extract_powershell_script_url(command=command) if platform.system() == "Windows" else None
    if powershell_script_url is None:
        result = subprocess.run(command, shell=True, capture_output=False, text=True, encoding="utf-8", check=False)
    else:
        result = _run_downloaded_powershell_script(script_url=powershell_script_url)
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
