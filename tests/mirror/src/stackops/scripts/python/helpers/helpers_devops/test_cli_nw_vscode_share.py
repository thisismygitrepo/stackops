import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_nw, vscode_tunnel_auth


@pytest.mark.parametrize("action", ["run", "install-service"])
def test_vscode_tunnel_actions_show_credential_context(monkeypatch: pytest.MonkeyPatch, action: str) -> None:
    credential_checks: list[str] = []
    executed_scripts: list[str] = []

    def capture_credential_context(cli_data_dir: str | None) -> None:
        if cli_data_dir is not None:
            credential_checks.append(cli_data_dir)

    def capture_script(script: str) -> None:
        executed_scripts.append(script)

    monkeypatch.setattr(vscode_tunnel_auth, "print_vscode_tunnel_credential_context", capture_credential_context)
    monkeypatch.setattr("stackops.utils.code.exit_then_run_shell_script", capture_script)

    result = CliRunner().invoke(cli_nw.get_app(), ["vscode-share", action, "--name", "labbox", "--cli-data-dir", "/tmp/work account"])

    assert result.exit_code == 0, result.output
    assert credential_checks == ["/tmp/work account"]
    assert len(executed_scripts) == 1
    assert executed_scripts[0].startswith("code tunnel")
    assert "--cli-data-dir '/tmp/work account'" in executed_scripts[0]


def test_vscode_share_rejects_cli_data_dir_inside_extra_args() -> None:
    result = CliRunner().invoke(cli_nw.get_app(), ["vscode-share", "run", "--extra-args=--cli-data-dir=/tmp/work"])

    assert result.exit_code == 2
    assert "Pass this option directly to vscode-share" in result.output
    assert "instead of through --extra-args" in result.output
