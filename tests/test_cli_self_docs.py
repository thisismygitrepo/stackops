from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_devops import cli_self, cli_self_docs


runner = CliRunner()


def test_docs_command_passes_rebuild_flag() -> None:
    with patch.object(cli_self_docs, "serve_docs") as serve_docs:
        result = runner.invoke(cli_self.get_app(), ["docs", "-b"])

    assert result.exit_code == 0
    serve_docs.assert_called_once_with(rebuild=True, create_artifacts=False)


def test_docs_command_passes_create_artifacts_flag() -> None:
    with patch.object(cli_self_docs, "serve_docs") as serve_docs:
        result = runner.invoke(cli_self.get_app(), ["docs", "--create-artifacts"])

    assert result.exit_code == 0
    serve_docs.assert_called_once_with(rebuild=False, create_artifacts=True)


def test_serve_docs_rebuilds_before_serving() -> None:
    with (
        patch.object(cli_self_docs, "get_docs_repo_root", return_value=Path("/repo")),
        patch.object(cli_self_docs, "_print_docs_urls"),
        patch("platform.system", return_value="Linux"),
        patch("machineconfig.utils.code.get_uv_command", return_value="uv"),
        patch("machineconfig.scripts.python.helpers.helpers_devops.docs_changelog.sync_docs_changelog") as sync_docs_changelog,
        patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script,
    ):
        cli_self_docs.serve_docs(rebuild=True, create_artifacts=False)

    script = exit_then_run_shell_script.call_args.kwargs["script"]
    sync_docs_changelog.assert_called_once_with(repo_root=Path("/repo"))
    assert "uv run zensical build" in script
    assert script.index("uv run zensical build") < script.index("uv run zensical serve -a 0.0.0.0:8000")


def test_serve_docs_skips_rebuild_when_disabled() -> None:
    with (
        patch.object(cli_self_docs, "get_docs_repo_root", return_value=Path("/repo")),
        patch.object(cli_self_docs, "_print_docs_urls"),
        patch("platform.system", return_value="Linux"),
        patch("machineconfig.utils.code.get_uv_command", return_value="uv"),
        patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script,
    ):
        cli_self_docs.serve_docs(rebuild=False, create_artifacts=False)

    script = exit_then_run_shell_script.call_args.kwargs["script"]
    assert "uv run zensical build" not in script


def test_serve_docs_creates_artifacts_before_serving() -> None:
    with (
        patch.object(cli_self_docs, "get_docs_repo_root", return_value=Path("/repo")),
        patch.object(cli_self_docs, "_print_docs_urls"),
        patch.object(cli_self_docs, "create_docs_artifacts") as create_docs_artifacts,
        patch("platform.system", return_value="Linux"),
        patch("machineconfig.utils.code.get_uv_command", return_value="uv"),
        patch("machineconfig.utils.code.exit_then_run_shell_script") as exit_then_run_shell_script,
    ):
        cli_self_docs.serve_docs(rebuild=False, create_artifacts=True)

    create_docs_artifacts.assert_called_once_with(repo_root=Path("/repo"))
    script = exit_then_run_shell_script.call_args.kwargs["script"]
    assert "uv run zensical serve -a 0.0.0.0:8000" in script


def test_create_docs_artifacts_regenerates_cli_graph_and_plotly_views(tmp_path: Path) -> None:
    render_calls: list[tuple[str, str, str]] = []

    def _record_render(*, view: str, output: str, template: str, **_kwargs: object) -> None:
        render_calls.append((view, output, template))

    with (
        patch.object(cli_self_docs, "_write_cli_graph_snapshot") as write_cli_graph_snapshot,
        patch("machineconfig.scripts.python.graph.visualize.plotly_views.use_render_plotly", side_effect=_record_render),
    ):
        generated_paths = cli_self_docs.create_docs_artifacts(repo_root=tmp_path)

    write_cli_graph_snapshot.assert_called_once_with(repo_root=tmp_path)
    expected_paths = [tmp_path.joinpath(spec.output_relative_path) for spec in cli_self_docs.DOCS_ARTIFACT_SPECS]
    assert generated_paths == expected_paths
    assert render_calls == [
        (spec.view, str(tmp_path.joinpath(spec.output_relative_path)), "plotly_dark")
        for spec in cli_self_docs.DOCS_ARTIFACT_SPECS
    ]


def test_get_docs_repo_root_accepts_zensical_config(tmp_path: Path) -> None:
    docs_dir = tmp_path.joinpath("docs")
    docs_dir.mkdir()
    tmp_path.joinpath("zensical.toml").write_text("", encoding="utf-8")

    with patch("machineconfig.utils.source_of_truth.REPO_ROOT", tmp_path):
        assert cli_self_docs.get_docs_repo_root() == tmp_path


def test_get_docs_repo_root_rejects_missing_zensical_config(tmp_path: Path) -> None:
    docs_dir = tmp_path.joinpath("docs")
    docs_dir.mkdir()

    with patch("machineconfig.utils.source_of_truth.REPO_ROOT", tmp_path), pytest.raises(typer.Exit) as exc_info:
        cli_self_docs.get_docs_repo_root()

    assert exc_info.value.exit_code == 1
