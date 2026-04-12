from __future__ import annotations

from pathlib import Path
import sys
import types

import pytest

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_debug_linux as target


def _noop_print(*_args: object, **_kwargs: object) -> None:
    return None


def _map_posix_path(root_dir: Path, value: str | Path) -> Path:
    raw_path = Path(value)
    if raw_path.is_absolute():
        return root_dir.joinpath(*raw_path.parts[1:])
    return raw_path


def _build_path_class(root_dir: Path, home_dir: Path) -> type[object]:
    class MappedPath:
        @classmethod
        def home(cls) -> Path:
            return home_dir

        def __new__(cls, value: str | Path) -> Path:
            return _map_posix_path(root_dir=root_dir, value=value)

    return MappedPath


def test_ssh_debug_linux_delegates_to_darwin(monkeypatch: pytest.MonkeyPatch) -> None:
    module_name = "machineconfig.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin"
    fake_module = types.ModuleType(module_name)
    fake_result = {"delegated": {"status": "ok", "message": "darwin"}}
    setattr(fake_module, "ssh_debug_darwin", lambda: fake_result)

    monkeypatch.setattr(target, "system", lambda: "Darwin")
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    assert target.ssh_debug_linux() == fake_result


def test_ssh_debug_linux_applies_cloud_init_password_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root_dir = tmp_path.joinpath("root")
    home_dir = root_dir.joinpath("home", "tester")
    ssh_dir = home_dir.joinpath(".ssh")
    ssh_dir.mkdir(parents=True)
    home_dir.chmod(0o755)
    ssh_dir.chmod(0o700)
    ssh_dir.joinpath("authorized_keys").write_text("ssh-ed25519 AAAA key\n", encoding="utf-8")
    ssh_dir.joinpath("authorized_keys").chmod(0o600)
    etc_ssh = root_dir.joinpath("etc", "ssh")
    etc_ssh.mkdir(parents=True)
    root_dir.joinpath("tmp").mkdir(parents=True)
    etc_ssh.joinpath("sshd_config").write_text(
        """
Port 22
PubkeyAuthentication yes
PasswordAuthentication yes
""".strip(),
        encoding="utf-8",
    )
    override_dir = etc_ssh.joinpath("sshd_config.d")
    override_dir.mkdir()
    override_dir.joinpath("50-cloud-init.conf").write_text("PasswordAuthentication no\n", encoding="utf-8")

    command_results: dict[tuple[str, ...], tuple[bool, str]] = {
        ("hostname",): (True, "linux-host"),
        ("systemctl", "is-active", "ssh"): (True, "active"),
        ("systemctl", "is-active", "sshd"): (False, ""),
        ("ip", "addr", "show"): (True, "2: eth0    inet 10.0.0.5/24 brd 10.0.0.255 scope global eth0"),
        ("ss", "-tlnp"): (True, "LISTEN 0 128 0.0.0.0:22 0.0.0.0:* users:(('sshd',pid=1,fd=3))"),
        ("getenforce",): (True, "Permissive"),
    }

    monkeypatch.setattr(target, "system", lambda: "Linux")
    monkeypatch.setattr(target, "check_sshd_installed", lambda: (True, "/usr/sbin/sshd"))
    monkeypatch.setattr(target, "detect_package_manager", lambda: ("apt", "sudo apt install openssh-server"))
    monkeypatch.setattr(target, "run_cmd", lambda cmd: command_results.get(tuple(cmd), (False, "")))
    monkeypatch.setattr(target, "Path", _build_path_class(root_dir=root_dir, home_dir=home_dir))
    monkeypatch.setattr(target.console, "print", _noop_print)

    results = target.ssh_debug_linux()

    assert results["installation"]["status"] == "ok"
    assert results["ssh_service"]["status"] == "ok"
    assert results["authorized_keys"]["status"] == "ok"
    assert results["password_auth"]["status"] == "info"
    assert results["ssh_listening"]["status"] == "ok"
    assert root_dir.joinpath("tmp", "ssh_fix.sh").is_file()
