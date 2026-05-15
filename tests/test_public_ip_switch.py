import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_network import address_switch
from stackops.utils.installer_utils import installer_cli


def test_switch_public_ip_address_shows_attempted_ips_and_pool_reason(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(installer_cli, "install_if_missing", lambda which, binary_name, verbose: None)
    monkeypatch.setattr(address_switch.time, "sleep", lambda _seconds: None)

    observed_commands: list[tuple[str, ...]] = []

    def fake_run(command: list[str]) -> subprocess.CompletedProcess[str]:
        observed_commands.append(tuple(command))
        match command:
            case ["warp-cli", "registration", "delete"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="", stderr="")
            case ["warp-cli", "registration", "new"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="Success\n", stderr="")
            case ["warp-cli", "connect"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="Success\n", stderr="")
            case ["warp-cli", "status"]:
                return subprocess.CompletedProcess(args=command, returncode=0, stdout="Status update: Connected\nNetwork: healthy\n", stderr="")
            case _:
                raise AssertionError(f"Unexpected command: {command}")

    ip_sequence = iter(["104.28.154.159", "104.28.162.208", "104.28.163.96"])

    monkeypatch.setattr(address_switch, "_run_command", fake_run)
    monkeypatch.setattr(address_switch, "get_public_ip_address", lambda: {"ip": next(ip_sequence)})

    success, new_ip = address_switch.switch_public_ip_address(max_trials=2, wait_seconds=5.0, target_ip_addresses=["104.28.163.96"])

    rendered = capsys.readouterr().out

    assert success is True
    assert new_ip == "104.28.163.96"
    assert "IPs attempted so far" in rendered
    assert "104.28.162.208" in rendered
    assert "104.28.163.96" in rendered
    assert "This IP is not acceptable because it's not within this pool: 104.28.163.96." in rendered
    assert "Acceptable IP pool:" in rendered
    assert observed_commands == [
        ("warp-cli", "registration", "delete"),
        ("warp-cli", "registration", "new"),
        ("warp-cli", "connect"),
        ("warp-cli", "status"),
        ("warp-cli", "registration", "delete"),
        ("warp-cli", "registration", "new"),
        ("warp-cli", "connect"),
        ("warp-cli", "status"),
    ]
