from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_devops import cli_self, cli_self_assets, cli_self_docs


runner = CliRunner()


def test_update_cli_graph_command_calls_snapshot_writer() -> None:
    with (
        patch.object(cli_self_docs, "get_docs_repo_root", return_value=Path("/repo")),
        patch.object(cli_self_docs, "write_cli_graph_snapshot") as write_cli_graph_snapshot,
    ):
        result = runner.invoke(cli_self_assets.get_app(), ["update-cli-graph"])

    assert result.exit_code == 0
    write_cli_graph_snapshot.assert_called_once_with(repo_root=Path("/repo"))


def test_regenerate_charts_command_calls_sunburst_renderer() -> None:
    with (
        patch.object(cli_self_docs, "get_docs_repo_root", return_value=Path("/repo")),
        patch.object(cli_self_docs, "render_docs_artifact") as render_docs_artifact,
    ):
        result = runner.invoke(cli_self_assets.get_app(), ["regenerate-charts"])

    assert result.exit_code == 0
    render_docs_artifact.assert_called_once()
    assert render_docs_artifact.call_args.kwargs["repo_root"] == Path("/repo")
    artifact_spec = render_docs_artifact.call_args.kwargs["artifact_spec"]
    assert artifact_spec.view == "sunburst"
    assert artifact_spec.output_relative_path == Path("docs/assets/devops-self-explore/sunburst.html")


def test_self_app_registers_assets_subapp_when_local_repo_exists(tmp_path: Path) -> None:
    fake_home = tmp_path
    fake_home.joinpath("code", "machineconfig").mkdir(parents=True)

    with patch.object(cli_self.Path, "home", return_value=fake_home):
        result = runner.invoke(cli_self.get_app(), ["build-assets", "--help"])

    assert result.exit_code == 0
    assert "update-cli-graph" in result.output
    assert "regenerate-charts" in result.output


def test_self_app_omits_assets_subapp_when_local_repo_missing(tmp_path: Path) -> None:
    with patch.object(cli_self.Path, "home", return_value=tmp_path):
        result = runner.invoke(cli_self.get_app(), ["build-assets", "--help"])

    assert result.exit_code != 0
    assert "No such command 'build-assets'" in result.output
