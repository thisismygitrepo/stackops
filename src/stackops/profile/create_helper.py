
from typing import Literal
from pathlib import Path
import stat
import shutil
from stackops.utils.source_of_truth import LIBRARY_ROOT, CONFIG_ROOT


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


def _add_execute_bit(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _make_scripts_executable(scripts_path: Path) -> None:
    _add_execute_bit(scripts_path)
    for path in scripts_path.rglob("*"):
        _add_execute_bit(path)


def copy_assets_to_machine(which: Literal["scripts", "settings"]) -> None:
    import platform
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

        wrap_stackops_source = LIBRARY_ROOT.joinpath("scripts", "nu", "wrap_stackops.nu")
        wrap_stackops_target = CONFIG_ROOT.joinpath("scripts", "wrap_stackops.nu")

        wrap_stackops_target.parent.mkdir(parents=True, exist_ok=True)
        _copy_path(source=wrap_stackops_source, target=wrap_stackops_target, overwrite=True)

        if system_name in {"linux", "darwin"}:
            from rich.console import Console
            console = Console()
            console.print("\n[bold]📜 Setting executable permissions for scripts...[/bold]")
            scripts_path = CONFIG_ROOT.joinpath("scripts")
            _make_scripts_executable(scripts_path)
            console.print("[green]✅ Script permissions updated[/green]")
        return

    source = LIBRARY_ROOT.joinpath("settings")
    target = CONFIG_ROOT.joinpath("settings")

    _copy_path(source=source, target=target, overwrite=True)
    
