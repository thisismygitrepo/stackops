from __future__ import annotations

import sys
from types import ModuleType

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_devops import cli_ssh as module


def install_helpers_network_ssh_submodule(
    monkeypatch: pytest.MonkeyPatch,
    leaf_name: str,
    leaf_module: ModuleType,
) -> None:
    import machineconfig.scripts.python.helpers as helpers_package

    helpers_network_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network")
    ssh_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network.ssh")
    setattr(ssh_module, leaf_name, leaf_module)
    setattr(helpers_network_module, "ssh", ssh_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network", helpers_network_module)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_network.ssh", ssh_module)
    monkeypatch.setitem(sys.modules, f"machineconfig.scripts.python.helpers.helpers_network.ssh.{leaf_name}", leaf_module)
    monkeypatch.setattr(helpers_package, "helpers_network", helpers_network_module, raising=False)


def test_get_windows_ssh_server_install_script_switches_install_method() -> None:
    winget_script = module._get_windows_ssh_server_install_script(use_winget=True)
    capability_script = module._get_windows_ssh_server_install_script(use_winget=False)

    assert "winget install --no-upgrade --Id Microsoft.OpenSSH.Preview" in winget_script
    assert 'C:\\Program Files\\OpenSSH\\sshd.exe' in winget_script
    assert "Add-WindowsCapability -Online -Name OpenSSH.Server" in capability_script
    assert '$env:WINDIR\\System32\\OpenSSH\\sshd.exe' in capability_script


def test_install_ssh_server_runs_linux_script(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    recorded_calls: list[tuple[str, bool, bool]] = []
    code_module = ModuleType("machineconfig.utils.code")

    def fake_run_shell_script(*, script: str, display_script: bool, clean_env: bool) -> None:
        recorded_calls.append((script, display_script, clean_env))

    setattr(code_module, "run_shell_script", fake_run_shell_script)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.code", code_module)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    module.install_ssh_server()

    assert recorded_calls == [
        (
            """
sudo nala install openssh-server -y || true  # try to install first
# sudo nala purge openssh-server -y
# sudo nala install openssh-server -y
echo \"✅ FINISHED installing openssh-server.\"
""",
            True,
            False,
        )
    ]


def test_install_ssh_server_exits_on_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    monkeypatch.setattr(platform, "system", lambda: "Plan9")

    with pytest.raises(typer.Exit) as exc_info:
        module.install_ssh_server()

    assert exc_info.value.exit_code == 1


def test_change_ssh_port_requires_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    monkeypatch.setattr(platform, "system", lambda: "Windows")

    with pytest.raises(typer.Exit) as exc_info:
        module.change_ssh_port(port=2222)

    assert exc_info.value.exit_code == 1


def test_change_ssh_port_forwards_to_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    helper_module = ModuleType("machineconfig.utils.ssh_utils.wsl")
    recorded_ports: list[int] = []

    def fake_change_ssh_port(*, port: int) -> None:
        recorded_ports.append(port)

    setattr(helper_module, "change_ssh_port", fake_change_ssh_port)
    monkeypatch.setitem(sys.modules, "machineconfig.utils.ssh_utils.wsl", helper_module)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    module.change_ssh_port(port=2200)

    assert recorded_ports == [2200]


def test_add_ssh_key_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    helper_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network.ssh.ssh_add_ssh_key")
    recorded_calls: list[tuple[str | None, bool, bool, str | None, str | None]] = []

    def fake_main(*, pub_path: str | None, pub_choose: bool, pub_val: bool, from_github: str | None, remote: str | None) -> None:
        recorded_calls.append((pub_path, pub_choose, pub_val, from_github, remote))

    setattr(helper_module, "main", fake_main)
    install_helpers_network_ssh_submodule(monkeypatch, "ssh_add_ssh_key", helper_module)

    module.add_ssh_key(path="/tmp/key.pub", choose=True, value=False, github="alex", remote="root@host:22")

    assert recorded_calls == [("/tmp/key.pub", True, False, "alex", "root@host:22")]


def test_debug_ssh_dispatches_to_linux_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    import platform

    helper_module = ModuleType("machineconfig.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux")
    recorded_calls: list[str] = []

    def fake_ssh_debug_linux() -> None:
        recorded_calls.append("linux")

    setattr(helper_module, "ssh_debug_linux", fake_ssh_debug_linux)
    install_helpers_network_ssh_submodule(monkeypatch, "ssh_debug_linux", helper_module)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    module.debug_ssh()

    assert recorded_calls == ["linux"]


def test_get_app_registers_expected_commands() -> None:
    app = module.get_app()
    command_names = [command_info.name for command_info in app.registered_commands]

    assert command_names == ["install-server", "i", "change-port", "p", "add-key", "k", "debug", "d"]
