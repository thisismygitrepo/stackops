from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_device, cli_device_port
from stackops.utils.ssh_utils.connection_target import SSHConnectionTarget


@pytest.mark.parametrize(
    ("destination", "hostname", "username", "port"),
    [
        ("workstation", "workstation", "local-user", 22),
        ("alex@workstation", "workstation", "alex", 22),
        ("workstation:2222", "workstation", "local-user", 2_222),
        ("alex@workstation:2222", "workstation", "alex", 2_222),
        ("2001:db8::10", "2001:db8::10", "local-user", 22),
        ("[2001:db8::10]:2222", "2001:db8::10", "local-user", 2_222),
        ("alex@[2001:db8::10]:2222", "2001:db8::10", "alex", 2_222),
    ],
)
def test_resolve_map_port_destination_supports_every_ssh_destination_form(
    monkeypatch: pytest.MonkeyPatch,
    destination: str,
    hostname: str,
    username: str,
    port: int,
) -> None:
    monkeypatch.setattr(cli_device_port.getpass, "getuser", lambda: "local-user")
    monkeypatch.setattr(
        cli_device_port,
        "lookup_open_ssh_config",
        lambda requested_hostname, _requested_username, _requested_port: {"hostname": requested_hostname},
    )

    target = cli_device_port.resolve_map_port_destination(destination=destination)

    assert target == SSHConnectionTarget(
        host=destination,
        hostname=hostname,
        username=username,
        port=port,
        ssh_key_path=None,
        proxy_command=None,
    )


def test_resolve_map_port_destination_uses_supported_ssh_config_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identity_file = tmp_path / "workstation-key"
    identity_file.touch()
    lookup_arguments: list[tuple[str, str | None, int | None]] = []

    def lookup_config(hostname: str, username: str | None, port: int | None) -> dict[str, object]:
        lookup_arguments.append((hostname, username, port))
        return {
            "hostname": "workstation.internal",
            "user": "remote-user",
            "port": "2200",
            "identityfile": [str(identity_file)],
            "proxyjump": "jump-user@gateway:2222",
        }

    monkeypatch.setattr(cli_device_port.getpass, "getuser", lambda: "local-user")
    monkeypatch.setattr(cli_device_port, "lookup_open_ssh_config", lookup_config)

    target = cli_device_port.resolve_map_port_destination(destination="workstation")

    assert lookup_arguments == [("workstation", None, None)]
    assert target == SSHConnectionTarget(
        host="workstation",
        hostname="workstation.internal",
        username="remote-user",
        port=2_200,
        ssh_key_path=str(identity_file),
        proxy_command="ssh -T -l jump-user -p 2222 -W workstation.internal:2200 -- gateway",
    )


def test_build_map_port_command_owns_a_clean_foreground_connection() -> None:
    target = SSHConnectionTarget(
        host="workstation",
        hostname="workstation.internal",
        username="alex",
        port=2_222,
        ssh_key_path="/keys/workstation",
        proxy_command="ssh gateway -W workstation.internal:2222",
    )

    command = cli_device_port.build_map_port_command(ssh_destination=target, remote_port=8_000, local_port=9_000)

    assert command == (
        "ssh",
        "-F",
        cli_device_port.os.devnull,
        "-N",
        "-T",
        "-o",
        "ExitOnForwardFailure=yes",
        "-o",
        "ForkAfterAuthentication=no",
        "-o",
        "ControlMaster=no",
        "-S",
        "none",
        "-L",
        "127.0.0.1:9000:127.0.0.1:8000",
        "-i",
        "/keys/workstation",
        "-o",
        "ProxyCommand=ssh gateway -W workstation.internal:2222",
        "-l",
        "alex",
        "-p",
        "2222",
        "--",
        "workstation.internal",
    )


@pytest.mark.parametrize(("remote_port", "local_port"), [(0, 8_000), (65_536, 8_000), (8_000, 0), (8_000, 65_536)])
def test_build_map_port_command_rejects_invalid_ports(remote_port: int, local_port: int) -> None:
    target = SSHConnectionTarget(
        host="workstation",
        hostname="workstation.internal",
        username="alex",
        port=22,
        ssh_key_path=None,
        proxy_command=None,
    )
    with pytest.raises(ValueError, match="must be between 1 and 65535"):
        cli_device_port.build_map_port_command(ssh_destination=target, remote_port=remote_port, local_port=local_port)


def _resolved_workstation(destination: str) -> SSHConnectionTarget:
    return SSHConnectionTarget(
        host=destination,
        hostname="workstation.internal",
        username="alex",
        port=22,
        ssh_key_path=None,
        proxy_command=None,
    )


def test_device_map_port_and_alias_run_the_same_loopback_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    class CompletedPopen:
        def __init__(self, command: tuple[str, ...]) -> None:
            self.command = command

        def wait(self) -> int:
            return 0

    def record_popen(command: tuple[str, ...]) -> CompletedPopen:
        commands.append(command)
        return CompletedPopen(command=command)

    monkeypatch.setattr(cli_device_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_device_port.subprocess, "Popen", record_popen)
    app = cli_device.get_app()
    runner = CliRunner()

    command_result = runner.invoke(app, ["map-port", "workstation", "8000"])
    alias_result = runner.invoke(app, ["m", "workstation", "8000", "--local-port", "9000"])

    assert command_result.exit_code == 0, command_result.output
    assert alias_result.exit_code == 0, alias_result.output
    assert "127.0.0.1:8000:127.0.0.1:8000" in commands[0]
    assert "127.0.0.1:9000:127.0.0.1:8000" in commands[1]


def test_device_map_port_is_visible_and_alias_is_hidden() -> None:
    result = CliRunner().invoke(cli_device.get_app(), ["--help"], terminal_width=160)

    assert result.exit_code == 0, result.output
    assert "map-port" in result.output
    assert "<m> Map a remote TCP port" in result.output
    assert "over SSH" in result.output
    assert "\n│ m " not in result.output


def test_device_map_port_propagates_ssh_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailedPopen:
        def wait(self) -> int:
            return 23

    def fail_popen(_command: tuple[str, ...]) -> FailedPopen:
        return FailedPopen()

    monkeypatch.setattr(cli_device_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_device_port.subprocess, "Popen", fail_popen)

    result = CliRunner().invoke(cli_device.get_app(), ["map-port", "workstation", "8000"])

    assert result.exit_code == 23


def test_device_map_port_opens_the_mapped_local_address(monkeypatch: pytest.MonkeyPatch) -> None:
    opened_urls: list[str] = []

    class CompletedPopen:
        def wait(self) -> int:
            return 0

    def record_popen(_command: tuple[str, ...]) -> CompletedPopen:
        return CompletedPopen()

    def record_browser_open(url: str) -> bool:
        opened_urls.append(url)
        return True

    monkeypatch.setattr(cli_device_port, "resolve_map_port_destination", _resolved_workstation)
    monkeypatch.setattr(cli_device_port.subprocess, "Popen", record_popen)
    monkeypatch.setattr(cli_device_port.webbrowser, "open_new_tab", record_browser_open)

    result = CliRunner().invoke(cli_device.get_app(), ["map-port", "workstation", "8000", "-l", "9000", "-b"])

    assert result.exit_code == 0, result.output
    assert opened_urls == ["http://127.0.0.1:9000"]


def test_device_map_port_reports_malformed_destination() -> None:
    result = CliRunner().invoke(cli_device.get_app(), ["map-port", "bad@", "8000"])

    assert result.exit_code == 2
    assert "Invalid value for DESTINATION" in result.output
    assert "Invalid SSH destination: 'bad@'" in result.output


def test_device_map_port_reports_destination_rejected_by_openssh(monkeypatch: pytest.MonkeyPatch) -> None:
    def reject_destination(destination: str) -> SSHConnectionTarget:
        assert destination == "bad host"
        raise cli_device_port.subprocess.CalledProcessError(
            returncode=255,
            cmd=("ssh", "-G", "bad host"),
            stderr="invalid SSH host",
        )

    monkeypatch.setattr(cli_device_port, "resolve_map_port_destination", reject_destination)

    result = CliRunner().invoke(cli_device.get_app(), ["map-port", "bad host", "8000"])

    assert result.exit_code == 2
    assert "Invalid value for DESTINATION" in result.output
    assert "invalid SSH host" in result.output
