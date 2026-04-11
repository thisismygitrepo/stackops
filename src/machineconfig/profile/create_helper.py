
from typing import Literal
from pathlib import Path
import shutil
import machineconfig.scripts.nu as nu_scripts
from machineconfig.scripts.nu import WRAP_MCFG_PATH_REFERENCE
from machineconfig.utils.path_reference import get_path_reference_path
from machineconfig.utils.source_of_truth import LIBRARY_ROOT, CONFIG_ROOT


def _copy_path(source: Path, target: Path, overwrite: bool) -> None:
    source = source.expanduser().resolve()
    target = target.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Source path does not exist: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"Target already exists and overwrite=False: {target}")
    if target.exists() and overwrite:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if source.is_file():
        shutil.copy2(source, target)
    elif source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=overwrite)
    else:
        raise ValueError(f"Source is neither file nor directory: {source}")


def copy_assets_to_machine(which: Literal["scripts", "settings"]) -> None:
    import platform
    import subprocess
    system_name = platform.system().lower()
    if system_name == "windows":
        system = "windows"
    elif system_name in {"linux", "darwin"}:
        system = "linux"
    else:
        raise NotImplementedError(f"System {system_name} not supported")

    if which == "scripts":
        source = LIBRARY_ROOT.joinpath("scripts", system)
        target = CONFIG_ROOT.joinpath("scripts")

        for a_path in source.rglob("*"):
            if not a_path.is_file():
                continue
            relative_path = a_path.relative_to(source)
            target_path = target.joinpath(relative_path)
            _copy_path(source=a_path, target=target_path, overwrite=True)

        wrap_mcfg_source = get_path_reference_path(module=nu_scripts, path_reference=WRAP_MCFG_PATH_REFERENCE)
        wrap_mcfg_target = CONFIG_ROOT.joinpath("scripts", "wrap_mcfg.nu")

        wrap_mcfg_target.parent.mkdir(parents=True, exist_ok=True)
        _copy_path(source=wrap_mcfg_source, target=wrap_mcfg_target, overwrite=True)

        if system_name == "linux":
            from rich.console import Console
            console = Console()
            console.print("\n[bold]📜 Setting executable permissions for scripts...[/bold]")
            scripts_path = CONFIG_ROOT.joinpath("scripts")
            subprocess.run(f"chmod +x {scripts_path} -R", shell=True, capture_output=True, text=True, check=False)
            console.print("[green]✅ Script permissions updated[/green]")
        return

    source = LIBRARY_ROOT.joinpath("settings")
    target = CONFIG_ROOT.joinpath("settings")

    _copy_path(source=source, target=target, overwrite=True)
    
