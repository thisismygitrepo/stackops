from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from machineconfig.scripts.python.helpers.helpers_network.ssh import ssh_debug_windows as target


def _noop_print(*_args: object, **_kwargs: object) -> None:
    return None


def _map_windows_path(root_dir: Path, value: str | Path) -> Path:
    text = str(value).replace("\\", "/")
    if text.startswith("/"):
        return root_dir.joinpath(*Path(text).parts[1:])
    if len(text) >= 3 and text[1] == ":" and text[2] == "/":
        parts = [part for part in text[3:].split("/") if part != ""]
        return root_dir.joinpath(f"drive_{text[0].lower()}", *parts)
    return Path(text)


def _build_path_class(root_dir: Path, home_dir: Path) -> type[object]:
    class MappedPath:
        @classmethod
        def home(cls) -> Path:
            return home_dir

        def __new__(cls, value: str | Path) -> Path:
            return _map_windows_path(root_dir=root_dir, value=value)

    return MappedPath


def test_ssh_debug_windows_rejects_non_windows(monkeypatch: object) -> None:
    monkeypatch.setattr(target, "system", lambda: "Linux")

    with pytest.raises(NotImplementedError):
        target.ssh_debug_windows()


def test_ssh_debug_windows_uses_admin_authorized_keys_and_parses_config(
    monkeypatch: object,
    tmp_path: Path,
) -> None:
    root_dir = tmp_path.joinpath("root")
    home_dir = root_dir.joinpath("home", "tester")
    home_dir.mkdir(parents=True)
    config_dir = _map_windows_path(root_dir=root_dir, value="C:/ProgramData/ssh")
    config_dir.mkdir(parents=True)
    config_dir.joinpath("administrators_authorized_keys").write_text("ssh-ed25519 AAAA key\n", encoding="utf-8")
    config_dir.joinpath("sshd_config").write_text(
        """
Port 2222
PubkeyAuthentication yes
PasswordAuthentication no
""".strip(),
        encoding="utf-8",
    )

    def fake_run_powershell(command: str) -> tuple[bool, str]:
        command_map: dict[str, tuple[bool, str]] = {
            "hostname": (True, "win-host"),
            "Get-Service -Name sshd -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Status": (True, "Running"),
            "Get-Service -Name sshd | Select-Object -ExpandProperty StartType": (True, "Automatic"),
            "([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)": (
                True,
                "True",
            ),
            f'icacls "{config_dir.joinpath("administrators_authorized_keys")}"': (True, "BUILTIN\\Administrators:F\nNT AUTHORITY\\SYSTEM:F"),
            "Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp,Manual | Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*'} | Select-Object -ExpandProperty IPAddress": (
                True,
                "10.0.0.8",
            ),
        }
        if "Get-NetFirewallRule" in command:
            return (True, "Enabled : True\nAction : Allow")
        return command_map.get(command, (False, ""))

    def fake_netstat(
        _cmd: list[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        _ = (capture_output, text, check)
        return subprocess.CompletedProcess(
            args=["netstat", "-an"],
            returncode=0,
            stdout="  TCP    0.0.0.0:2222   0.0.0.0:0   LISTENING\n",
            stderr="",
        )

    monkeypatch.setattr(target, "system", lambda: "Windows")
    monkeypatch.setattr(target, "check_sshd_binary_exists", lambda: (True, "C:/Windows/System32/OpenSSH/sshd.exe"))
    monkeypatch.setattr(
        target,
        "detect_openssh",
        lambda: ("capability", _map_windows_path(root_dir=root_dir, value="C:/Windows/System32/OpenSSH/sshd.exe"), config_dir),
    )
    monkeypatch.setattr(target, "run_powershell", fake_run_powershell)
    monkeypatch.setattr(target, "Path", _build_path_class(root_dir=root_dir, home_dir=home_dir))
    monkeypatch.setattr(target.subprocess, "run", fake_netstat)
    monkeypatch.setattr(target.console, "print", _noop_print)

    results = target.ssh_debug_windows()

    assert results["installation"]["status"] == "ok"
    assert results["ssh_service"]["status"] == "ok"
    assert results["authorized_keys"]["status"] == "ok"
    assert results["pubkey_auth"]["status"] == "ok"
    assert results["password_auth"]["status"] == "info"
    assert results["ssh_listening"]["message"] == "Listening on port 2222"
    assert results["firewall"]["status"] == "ok"
