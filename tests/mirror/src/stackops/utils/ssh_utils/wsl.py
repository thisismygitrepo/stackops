from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess

from stackops.utils.ssh_utils import wsl as sut


def _make_path_factory(mappings: dict[str, Path]) -> Callable[..., Path]:
    real_path = Path

    def fake_path(*parts: object) -> Path:
        path_text = str(real_path(*[str(part) for part in parts]))
        mapped = mappings.get(path_text)
        if mapped is not None:
            return mapped
        return real_path(*[str(part) for part in parts])

    return fake_path


def test_copy_when_inside_wsl_copies_file_to_windows_home(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    windows_home = tmp_path / "windows"
    source_file = home_dir / "notes" / "source.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("payload", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(sut, "ensure_wsl_environment", lambda: None)
    monkeypatch.setattr(sut, "resolve_windows_home_from_wsl", lambda windows_username: windows_home)

    sut.copy_when_inside_wsl(source="notes/source.txt", target="backup/source.txt", overwrite=True, windows_username=None)

    assert windows_home.joinpath("backup", "source.txt").read_text(encoding="utf-8") == "payload"


def test_copy_when_inside_windows_removes_existing_target_before_copy(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    wsl_home = tmp_path / "wsl"
    source_file = home_dir / "docs" / "source.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("payload", encoding="utf-8")
    target_file = wsl_home / "backup" / "source.txt"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("old", encoding="utf-8")
    removed_paths: list[Path] = []
    copied_pairs: list[tuple[Path, Path]] = []
    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.setattr(sut, "ensure_windows_environment", lambda: None)
    monkeypatch.setattr(sut, "resolve_wsl_home_on_windows", lambda: wsl_home)
    monkeypatch.setattr(sut, "remove_path", lambda path: removed_paths.append(path))
    monkeypatch.setattr(sut, "run_windows_copy_command", lambda source_path, target_path: copied_pairs.append((source_path, target_path)))

    sut.copy_when_inside_windows(source="docs/source.txt", target="backup/source.txt", overwrite=True)

    assert removed_paths == [target_file]
    assert copied_pairs == [(source_file, target_file)]


def test_link_wsl_and_windows_uses_windows_branch_when_not_in_wsl(tmp_path: Path, monkeypatch) -> None:
    target_path = tmp_path / "wsl-home"
    target_path.mkdir()
    recorded_links: list[tuple[Path, Path]] = []
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(sut.platform, "system", lambda: "Windows")

    def raise_not_wsl() -> None:
        raise RuntimeError("not in wsl")

    monkeypatch.setattr(sut, "ensure_wsl_environment", raise_not_wsl)
    monkeypatch.setattr(sut, "ensure_windows_environment", lambda: None)
    monkeypatch.setattr(sut, "resolve_wsl_home_on_windows", lambda: target_path)
    monkeypatch.setattr(sut, "ensure_symlink", lambda link_path, desired_target: recorded_links.append((link_path, desired_target)) or True)

    sut.link_wsl_and_windows(windows_username=None)

    assert recorded_links == [(tmp_path / "wsl", target_path)]


def test_open_wsl_port_builds_powershell_array(monkeypatch) -> None:
    commands: list[list[str]] = []
    monkeypatch.setattr(sut, "ensure_windows_environment", lambda: None)

    def fake_run(args: list[str], capture_output: bool, text: bool) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text
        commands.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(sut.subprocess, "run", fake_run)

    sut.open_wsl_port("3000-3002, 8080")

    script = commands[0][4]
    assert "WSL Ports 3000-3002, 8080" in script
    assert "@('3000-3002','8080')" in script


def test_change_ssh_port_updates_config_and_override_files(tmp_path: Path, monkeypatch) -> None:
    sshd_config = tmp_path / "sshd_config"
    override_dir = tmp_path / "override.d"
    override_file = override_dir / "override.conf"
    sshd_config.write_text("#Port 22\nPermitRootLogin no\n", encoding="utf-8")
    monkeypatch.setattr(sut, "ensure_linux_environment", lambda: None)
    monkeypatch.setattr(sut, "Path", _make_path_factory({"/etc/ssh/sshd_config": sshd_config, "/etc/systemd/system/ssh.socket.d": override_dir}))
    recorded_commands: list[list[str]] = []

    def fake_run(
        args: list[str], input: bytes | None = None, capture_output: bool = False, check: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        _ = capture_output, check
        recorded_commands.append(args)
        if args == ["sudo", "tee", str(sshd_config)]:
            assert input is not None
            sshd_config.write_text(input.decode(), encoding="utf-8")
        elif args == ["sudo", "mkdir", "-p", str(override_dir)]:
            override_dir.mkdir(parents=True, exist_ok=True)
        elif args == ["sudo", "tee", str(override_file)]:
            assert input is not None
            override_file.write_text(input.decode(), encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(sut.subprocess, "run", fake_run)

    sut.change_ssh_port(2222)

    assert sshd_config.read_text(encoding="utf-8").startswith("Port 2222\n")
    assert override_file.read_text(encoding="utf-8") == "[Socket]\nListenStream=\nListenStream=2222\n"
    assert ["sudo", "systemctl", "daemon-reload"] in recorded_commands
    assert ["sudo", "systemctl", "restart", "ssh.socket"] in recorded_commands
    assert ["sudo", "service", "ssh", "restart"] in recorded_commands
