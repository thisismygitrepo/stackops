import subprocess

import pytest

from stackops.scripts.python.helpers.helpers_devops import vscode_tunnel_auth


@pytest.mark.parametrize(
    ("cli_data_dir", "expected_command", "command_output", "expected_provider"),
    [
        (
            "/tmp/work account",
            ["code", "tunnel", "user", "show", "--cli-data-dir", "/tmp/work account"],
            "logged in with provider GitHub Account\n",
            "GitHub Account",
        ),
        (None, ["code", "tunnel", "user", "show"], "logged in with provider Microsoft Account\n", "Microsoft Account"),
    ],
)
def test_get_vscode_tunnel_provider_uses_matching_cli_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    cli_data_dir: str | None,
    expected_command: list[str],
    command_output: str,
    expected_provider: vscode_tunnel_auth.VscodeTunnelProvider,
) -> None:
    def run_command(command: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        assert command == expected_command
        assert capture_output is True
        assert text is True
        assert check is False
        return subprocess.CompletedProcess(command, 0, stdout=command_output, stderr="")

    monkeypatch.setattr(vscode_tunnel_auth.subprocess, "run", run_command)

    assert vscode_tunnel_auth.get_vscode_tunnel_provider(cli_data_dir) == expected_provider


def test_get_vscode_tunnel_provider_recognizes_logged_out_launcher_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_command(command: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text, check
        return subprocess.CompletedProcess(command, 0, stdout="not logged in\n", stderr="")

    monkeypatch.setattr(vscode_tunnel_auth.subprocess, "run", run_command)

    assert vscode_tunnel_auth.get_vscode_tunnel_provider(None) is None


def test_get_vscode_tunnel_provider_rejects_unverifiable_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_command(command: list[str], *, capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        _ = capture_output, text, check
        return subprocess.CompletedProcess(command, 0, stdout="logged in\n", stderr="")

    monkeypatch.setattr(vscode_tunnel_auth.subprocess, "run", run_command)

    with pytest.raises(RuntimeError, match="Could not determine the VS Code tunnel credential provider: logged in"):
        vscode_tunnel_auth.get_vscode_tunnel_provider(None)
