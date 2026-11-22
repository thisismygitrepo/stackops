import platform
import shutil
import subprocess
from pathlib import Path

from stackops.utils.ssh_utils.wsl_helper import (
    ensure_relative_path,
    remove_path,
    ensure_wsl_environment,
    ensure_windows_environment,
    ensure_linux_environment,
    resolve_windows_home_from_wsl,
    resolve_wsl_home_on_windows,
    run_windows_copy_command,
    ensure_symlink,
    normalize_port_spec_for_firewall,
)


def _prepare_copy_target(home: Path, relative_target: Path, overwrite: bool) -> Path:
    target_path = home / relative_target
    if target_path.exists():
        if target_path.samefile(home):
            raise ValueError("Choose a transfer target below the destination home directory.")
        if not overwrite:
            raise FileExistsError(f"""Target already exists: {target_path}. Use --overwrite to replace it.""")
        remove_path(target_path)
    return target_path


def _prepare_copy_paths(source: Path | str, target: Path | str, remote_home: Path, source_is_remote: bool, overwrite: bool) -> tuple[Path, Path]:
    local_home = Path.home()
    source_home, target_home = (remote_home, local_home) if source_is_remote else (local_home, remote_home)
    source_path = source_home / ensure_relative_path(source)
    target_relative = ensure_relative_path(target)
    if not source_path.exists():
        raise FileNotFoundError(f"""Source does not exist: {source_path}. Check the source path and try again.""")
    return source_path, _prepare_copy_target(target_home, target_relative, overwrite)


def copy_when_inside_wsl(source: Path | str, target: Path | str, overwrite: bool, windows_username: str | None, *, source_is_remote: bool) -> None:
    ensure_wsl_environment()
    source_path, target_path = _prepare_copy_paths(source, target, resolve_windows_home_from_wsl(windows_username), source_is_remote, overwrite)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        shutil.copytree(source_path, target_path, dirs_exist_ok=False)
        return
    print(f"Copying {source_path} to {target_path}")
    shutil.copy2(source_path, target_path)


def copy_when_inside_windows(source: Path | str, target: Path | str, overwrite: bool, *, source_is_remote: bool) -> None:
    ensure_windows_environment()
    source_path, target_path = _prepare_copy_paths(source, target, resolve_wsl_home_on_windows(), source_is_remote, overwrite)
    run_windows_copy_command(source_path, target_path)


def link_wsl_and_windows(windows_username: str | None) -> None:
    system = platform.system()
    if system == "Darwin":
        raise RuntimeError("link_wsl_and_windows is not designed for macOS")
    try:
        ensure_wsl_environment()
    except RuntimeError:
        try:
            ensure_windows_environment()
        except RuntimeError as exc:
            raise RuntimeError("link_wsl_and_windows must run inside Windows or WSL") from exc
        print("🔗 Running inside Windows, linking to WSL home...")
        target_path = resolve_wsl_home_on_windows()
        link_path = Path.home() / "wsl"
        created = ensure_symlink(link_path, target_path)
        if created:
            print(f"✅ Created symlink: {link_path} -> {target_path}")
        else:
            print(f"✅ Symlink already exists: {link_path} -> {target_path}")
        return
    print("🔗 Running inside WSL, linking to Windows home...")
    target_path = resolve_windows_home_from_wsl(windows_username)
    link_path = Path.home() / "win"
    created = ensure_symlink(link_path, target_path)
    if created:
        print(f"✅ Created symlink: {link_path} -> {target_path}")
    else:
        print(f"✅ Symlink already exists: {link_path} -> {target_path}")


def open_wsl_port(ports_spec: str) -> None:
    ensure_windows_environment()
    normalized_ports, description = normalize_port_spec_for_firewall(ports_spec)
    rule_name = f"WSL Ports {description}"
    # Build PowerShell array syntax for -LocalPort parameter (e.g., @('3000-4000','8080'))
    port_parts = normalized_ports.split(",")
    ps_array = "@(" + ",".join(f"'{p}'" for p in port_parts) + ")"
    script = f"New-NetFirewallRule -DisplayName '{rule_name}' -Direction Inbound -LocalPort {ps_array} -Protocol TCP -Action Allow"
    print(f"🔥 Opening firewall for ports: {description}...")
    result = subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-Command", script], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        error_output = result.stderr.strip() or result.stdout.strip()
        if error_output:
            raise RuntimeError(f"Failed to create firewall rule for ports {description}: {error_output}")
        raise RuntimeError(f"Failed to create firewall rule for ports {description} with exit code {result.returncode}")
    print(f"✅ Firewall rule created for ports: {description}")


def change_ssh_port(port: int) -> None:
    ensure_linux_environment()
    from stackops.utils.ssh_utils.ssh_port_change import change_ssh_port_transaction

    change_ssh_port_transaction(target_port=port)


if __name__ == "__main__":
    copy_when_inside_wsl(Path("projects/source.txt"), Path("windows_projects/source.txt"), overwrite=True, windows_username=None, source_is_remote=False)
    copy_when_inside_windows(Path("documents/example.txt"), Path("linux_documents/example.txt"), overwrite=True, source_is_remote=False)
