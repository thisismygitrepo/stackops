import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_device, cli_device_port


@pytest.mark.parametrize(
    ("destination", "destination_arguments"),
    [
        ("workstation", ("--", "workstation")),
        ("alex@workstation", ("-l", "alex", "--", "workstation")),
        ("workstation:2222", ("-p", "2222", "--", "workstation")),
        ("alex@workstation:2222", ("-l", "alex", "-p", "2222", "--", "workstation")),
        ("2001:db8::10", ("--", "2001:db8::10")),
        ("[2001:db8::10]:2222", ("-p", "2222", "--", "2001:db8::10")),
        ("alex@[2001:db8::10]:2222", ("-l", "alex", "-p", "2222", "--", "2001:db8::10")),
    ],
)
def test_build_map_port_command_preserves_ssh_destination_forms(
    destination: str,
    destination_arguments: tuple[str, ...],
) -> None:
    command = cli_device_port.build_map_port_command(destination=destination, remote_port=8_000, local_port=9_000)

    assert command == (
        "ssh",
        "-N",
        "-T",
        "-o",
        "ExitOnForwardFailure=yes",
        "-L",
        "127.0.0.1:9000:127.0.0.1:8000",
        *destination_arguments,
    )


@pytest.mark.parametrize(("remote_port", "local_port"), [(0, 8_000), (65_536, 8_000), (8_000, 0), (8_000, 65_536)])
def test_build_map_port_command_rejects_invalid_ports(remote_port: int, local_port: int) -> None:
    with pytest.raises(ValueError, match="must be between 1 and 65535"):
        cli_device_port.build_map_port_command(destination="workstation", remote_port=remote_port, local_port=local_port)


def test_device_map_port_and_alias_run_the_same_loopback_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[tuple[str, ...]] = []

    def record_run(command: tuple[str, ...], *, check: bool) -> subprocess.CompletedProcess[bytes]:
        assert check is False
        commands.append(command)
        return subprocess.CompletedProcess(args=command, returncode=0)

    monkeypatch.setattr(cli_device_port.subprocess, "run", record_run)
    app = cli_device.get_app()
    runner = CliRunner()

    command_result = runner.invoke(app, ["map-port", "workstation", "8000"])
    alias_result = runner.invoke(app, ["m", "workstation", "8000", "--local-port", "9000"])

    assert command_result.exit_code == 0, command_result.output
    assert alias_result.exit_code == 0, alias_result.output
    assert commands[0][6] == "127.0.0.1:8000:127.0.0.1:8000"
    assert commands[1][6] == "127.0.0.1:9000:127.0.0.1:8000"


def test_device_map_port_is_visible_and_alias_is_hidden() -> None:
    result = CliRunner().invoke(cli_device.get_app(), ["--help"], terminal_width=160)

    assert result.exit_code == 0, result.output
    assert "map-port" in result.output
    assert "<m> Map a remote TCP port" in result.output
    assert "over SSH" in result.output
    assert "\n│ m " not in result.output


def test_device_map_port_propagates_ssh_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_run(command: tuple[str, ...], *, check: bool) -> subprocess.CompletedProcess[bytes]:
        assert check is False
        return subprocess.CompletedProcess(args=command, returncode=23)

    monkeypatch.setattr(cli_device_port.subprocess, "run", fail_run)

    result = CliRunner().invoke(cli_device.get_app(), ["map-port", "workstation", "8000"])

    assert result.exit_code == 23
