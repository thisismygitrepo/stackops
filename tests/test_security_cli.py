from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.jobs.installer.checks import security_cli
from machineconfig.scripts.python.helpers.helpers_repos import download_repo_licenses


runner = CliRunner()


def test_repo_licenses_command_passes_github_token() -> None:
    with patch.object(download_repo_licenses, "run_download") as run_download:
        result = runner.invoke(security_cli.get_app(), ["repo-licenses", "--github-token", "token-value"])

    assert result.exit_code == 0
    run_download.assert_called_once_with(github_token="token-value")


def test_repo_licenses_command_surfaces_missing_token_error() -> None:
    with patch.object(download_repo_licenses, "run_download", side_effect=RuntimeError("missing token")):
        result = runner.invoke(security_cli.get_app(), ["repo-licenses"])

    assert result.exit_code == 2
    assert "missing token" in result.output
