import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_device, cli_ssh, cli_ssh_port
from stackops.utils.ssh_utils.open_ssh_command import OpenSSHCommandDestination


def test_resolve_map_port_destination_validates_with_openssh_and_returns_parsed_destination(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    def record_run(command: tuple[str, ...], check: bool, capture_output: bool, encoding: str) -> subprocess.CompletedProcess[str]:
        assert check
        assert capture_output
        assert encoding == "utf-8"
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(cli_ssh_port.subprocess, "run", record_run)

    destination = cli_ssh_port.resolve_map_port_destination(destination="alex@workstation:2222")

    assert destination == OpenSSHCommandDestination(hostname="workstation", username="alex", port=2_222)
    assert commands == [("ssh", "-G", "-T", "-l", "alex", "-p", "2222", "--", "workstation")]


def test_build_map_port_command_owns_a_clean_foreground_connection() -> None:
    target = OpenSSHCommandDestination(hostname="workstation.internal", username="alex", port=2_222)

    command = cli_ssh_port.build_map_port_command(ssh_destination=target, remote_port=8_000, local_port=9_000)

    assert command == (
        "ssh",
        "-N",
        "-T",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ClearAllForwardings=no",
        "-o",
        "ForkAfterAuthentication=no",
        "-o",
        "ControlMaster=no",
        "-S",
        "none",
        "-L",
        "127.0.0.1:9000:127.0.0.1:8000",
        "-l",
        "alex",
        "-p",
        "2222",
        "--",
        "workstation.internal",
    )


@pytest.mark.parametrize(("remote_port", "local_port"), [(0, 8_000), (65_536, 8_000), (8_000, 0), (8_000, 65_536)])
def test_build_map_port_command_rejects_invalid_ports(remote_port: int, local_port: int) -> None:
    target = OpenSSHCommandDestination(hostname="workstation.internal", username="alex", port=22)
    with pytest.raises(ValueError, match="must be between 1 and 65535"):
        cli_ssh_port.build_map_port_command(ssh_destination=target, remote_port=remote_port, local_port=local_port)


def _resolved_workstation(destination: str) -> OpenSSHCommandDestination:
    return OpenSSHCommandDestination(hostname="workstation.internal", username="alex", port=None)


def test_ssh_map_port_and_alias_run_the_same_loopback_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    class CompletedPopen:
        def __init__(self, command: tuple[str, ...]) -> None:
            self.command = command

        def wait(self) -> int:
            return 0

    def record_popen(command: tuple[str, ...]) -> CompletedPopen:
        commands.append(command)
        return CompletedPopen(command=command)

    monkeypatch.setattr(cli_ssh_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_ssh_port.subprocess, "Popen", record_popen)
    app = cli_ssh.get_app()
    runner = CliRunner()

    command_result = runner.invoke(app, ["map-port", "workstation", "8000"])
    alias_result = runner.invoke(app, ["m", "workstation", "8000", "--local-port", "9000"])

    assert command_result.exit_code == 0, command_result.output
    assert alias_result.exit_code == 0, alias_result.output
    assert "127.0.0.1:8000:127.0.0.1:8000" in commands[0]
    assert "127.0.0.1:9000:127.0.0.1:8000" in commands[1]


def test_ssh_map_port_is_visible_and_alias_is_hidden() -> None:
    result = CliRunner().invoke(cli_ssh.get_app(), ["--help"], terminal_width=160)
    device_result = CliRunner().invoke(cli_device.get_app(), ["--help"], terminal_width=160)

    assert result.exit_code == 0, result.output
    assert device_result.exit_code == 0, device_result.output
    assert "map-port" in result.output
    assert "<m> Map a remote TCP port" in result.output
    assert "over SSH" in result.output
    assert "\n│ m " not in result.output
    assert "map-port" not in device_result.output


def test_ssh_map_port_propagates_ssh_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailedPopen:
        def wait(self) -> int:
            return 23

    def fail_popen(_command: tuple[str, ...]) -> FailedPopen:
        return FailedPopen()

    monkeypatch.setattr(cli_ssh_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_ssh_port.subprocess, "Popen", fail_popen)

    result = CliRunner().invoke(cli_ssh.get_app(), ["map-port", "workstation", "8000"])

    assert result.exit_code == 23


def test_ssh_map_port_opens_the_mapped_local_address_once_the_tunnel_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    opened_urls: list[str] = []
    readiness_checks: list[int] = []

    class CompletedPopen:
        def wait(self) -> int:
            return 0

    def record_popen(_command: tuple[str, ...]) -> CompletedPopen:
        return CompletedPopen()

    def tunnel_is_ready(ssh_process: CompletedPopen, local_port: int) -> None:
        readiness_checks.append(local_port)
        assert not opened_urls

    def record_browser_open(url: str) -> bool:
        opened_urls.append(url)
        return True

    monkeypatch.setattr(cli_ssh_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_ssh_port.subprocess, "Popen", record_popen)
    monkeypatch.setattr(cli_ssh_port, "wait_for_local_forward", tunnel_is_ready)
    monkeypatch.setattr(cli_ssh_port.webbrowser, "open_new_tab", record_browser_open)

    result = CliRunner().invoke(cli_ssh.get_app(), ["map-port", "workstation", "8000", "-l", "9000", "-b"])

    assert result.exit_code == 0, result.output
    assert readiness_checks == [9_000]
    assert opened_urls == ["http://127.0.0.1:9000"]


def test_ssh_map_port_does_not_open_the_browser_when_the_tunnel_exits_before_it_is_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    opened_urls: list[str] = []

    class ExitedPopen:
        def poll(self) -> int:
            return 255

        def wait(self) -> int:
            return 255

    def record_popen(_command: tuple[str, ...]) -> ExitedPopen:
        return ExitedPopen()

    def tunnel_exited(ssh_process: ExitedPopen, local_port: int) -> int:
        return ssh_process.poll()

    def record_browser_open(url: str) -> bool:
        opened_urls.append(url)
        return True

    monkeypatch.setattr(cli_ssh_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_ssh_port.subprocess, "Popen", record_popen)
    monkeypatch.setattr(cli_ssh_port, "wait_for_local_forward", tunnel_exited)
    monkeypatch.setattr(cli_ssh_port.webbrowser, "open_new_tab", record_browser_open)

    result = CliRunner().invoke(cli_ssh.get_app(), ["map-port", "workstation", "8000", "-l", "9000", "-b"])

    assert result.exit_code == 255
    assert opened_urls == []


def test_ssh_map_port_reports_malformed_destination() -> None:
    result = CliRunner().invoke(cli_ssh.get_app(), ["map-port", "bad@", "8000"])

    assert result.exit_code == 2
    assert "Invalid value for DESTINATION" in result.output
    assert "Invalid SSH destination: 'bad@'" in result.output


def test_ssh_map_port_reports_destination_rejected_by_openssh(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_destination(destination: str) -> OpenSSHCommandDestination:
        assert destination == "bad host"
        raise cli_ssh_port.subprocess.CalledProcessError(returncode=255, cmd=("ssh", "-G", "bad host"), stderr="invalid SSH host")

    monkeypatch.setattr(cli_ssh_port, "resolve_map_port_destination", reject_destination)

    result = CliRunner().invoke(cli_ssh.get_app(), ["map-port", "bad host", "8000"])

    assert result.exit_code == 2
    assert "Invalid value for DESTINATION" in result.output
    assert "invalid SSH host" in result.output
