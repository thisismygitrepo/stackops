"""Set Windows Terminal Settings"""

from stackops.utils.accessories import randstr
import stackops.utils.path_core as path_core
from stackops.utils.io import save_json
from stackops.utils.files.read import read_json
import platform
from pathlib import Path

# from uuid import uuid4
import os
from typing import Any
from rich import box
from rich.console import Console
from rich.panel import Panel


"""
Not to be confused:
* Windows Terminal & Windows Terminal Preview: The latter is the night release version of WT.
* Windows PowerShell & PowerShell: The latter is community developed and is available on all platforms.
* Windows Powershell comes preinstalled with the system, Powershell must be installed separately.
* Lastly, powershell has a preview version as well.
All settings are available on GitHub: https://aka.ms/terminal-profiles-schema
"""


console = Console()
system = platform.system()  # Linux or Windows

assert system == "Windows", "This script is only for Windows."


def render_banner(message: str, title: str, border_style: str, box_style: box.Box) -> None:
    console.print(Panel.fit(message, title=title, border_style=border_style, box=box_style, padding=(1, 4)))


def set_wt_settings(nerd_font: bool = True) -> None:
    console.print()
    render_banner("🔍 INITIALIZING TERMINAL SETTINGS 🔍", "Windows Terminal", "cyan", box.DOUBLE)
    console.print()

    tmp = os.getenv("LOCALAPPDATA")
    if not isinstance(tmp, str):
        console.print("❌ ERROR: Could not find LOCALAPPDATA environment variable!")
        raise ValueError("Could not find LOCALAPPDATA environment variable.")

    settings_path = Path(tmp).joinpath(r"Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json")
    backup_name = f".orig_{randstr()}"
    console.print(f"📝 Creating backup of original settings as {backup_name}...")
    path_core.copy(settings_path, append=backup_name)
    console.print(f"📂 Loading Windows Terminal settings from: {settings_path}")
    data: dict[str, Any] = read_json(settings_path)
    profiles = list(data["profiles"]["list"])
    console.print(Panel(f"✅ Successfully loaded {len(profiles)} profiles", title="[bold blue]Terminal Settings[/bold blue]", border_style="blue", box=box.ROUNDED))

    console.print()
    console.print("⚙️  Updating default terminal settings...")
    data["startOnUserLogin"] = True
    data["launchMode"] = "fullscreen"
    data["theme"] = "dark"
    data["focusFollowMouse"] = True
    data["copyOnSelect"] = True
    data["profiles"]["defaults"]["padding"] = "0"
    data["profiles"]["defaults"]["useAcrylic"] = False
    console.print(Panel("✅ Default settings updated", title="[bold blue]Terminal Settings[/bold blue]", border_style="blue", box=box.ROUNDED))

    console.print()
    console.print("🛠️  Customizing PowerShell profile...")
    pwsh: dict[str, Any] = dict(
        name="PowerShell",
        commandline="pwsh",
        hidden=False,
        opacity=87,
        # guid="{" + str(uuid4()) + "}",  # WT doesn't accept any GUID to identify pwsh
        startingDirectory="%USERPROFILE%",  # "%USERPROFILE%",   # None: inherent from parent process.
    )
    if nerd_font:
        console.print("🔤 Setting PowerShell font to CaskaydiaCove Nerd Font...")
        pwsh["font"] = dict(face="CaskaydiaCove Nerd Font")  # because oh-my-posh uses glyphs from this font.

    powershell_profile = None
    for profile in profiles:
        if profile["name"] == "PowerShell":
            profile.update(pwsh)
            powershell_profile = profile
            console.print(Panel("✅ PowerShell profile customized successfully", title="[bold blue]Terminal Settings[/bold blue]", border_style="blue", box=box.ROUNDED))
            break
    else:
        console.print(Panel("❌ Couldn't customize PowerShell because profile not found, try to install it first.", title="[bold red]Terminal Settings[/bold red]", border_style="red", box=box.ROUNDED))

    console.print()
    console.print("🌟 Setting PowerShell as the default profile...")
    if powershell_profile is not None:
        data["defaultProfile"] = powershell_profile["guid"]
        console.print(Panel("✅ PowerShell is now the default profile!", title="[bold blue]Terminal Settings[/bold blue]", border_style="blue", box=box.ROUNDED))
    else:
        console.print(Panel("❌ PowerShell profile was not found in the list of profiles and therefore was not made the default.", title="[bold red]Terminal Settings[/bold red]", border_style="red", box=box.ROUNDED))

    console.print("⌨️  Adding keyboard shortcut for pane zoom (ctrl+shift+z)...")
    data["actions"].append({"command": "togglePaneZoom", "keys": "ctrl+shift+z"})

    console.print()
    console.print(f"💾 Saving terminal settings to: {settings_path}")
    data["profiles"]["list"] = profiles
    save_json(obj=data, path=settings_path, indent=5)
    console.print(Panel("✅ Settings saved successfully!", title="[bold blue]Terminal Settings[/bold blue]", border_style="blue", box=box.ROUNDED))


def main():
    console.print()
    render_banner("🖥️  WINDOWS TERMINAL SETUP 🖥️", "Windows Terminal", "cyan", box.DOUBLE)
    console.print()
    shell = {"powershell": "pwsh.exe", "Windows Powershell": "powershell.exe"}["powershell"].split(".exe", maxsplit=1)[0]
    if shell == "pwsh":
        console.print("🚀 Starting Windows Terminal configuration with PowerShell...")
        set_wt_settings(nerd_font=True)
        console.print()
        render_banner("✨ WINDOWS TERMINAL SETUP COMPLETE ✨", "Windows Terminal", "green", box.DOUBLE)
        console.print()
    else:
        error_msg = "❌ ERROR: Only PowerShell is supported, not Windows PowerShell!"
        console.print(error_msg)
        raise NotImplementedError(error_msg)


if __name__ == "__main__":
    pass
