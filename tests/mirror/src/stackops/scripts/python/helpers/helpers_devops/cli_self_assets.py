

from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_self_assets as module


RUNNER = CliRunner()


def test_update_cli_graph_uses_docs_repo_root(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    recorded_repo_roots: list[Path] = []

    def fake_get_docs_repo_root() -> Path:
        return repo_root

    def fake_write_cli_graph_snapshot(*, repo_root: Path) -> Path:
        recorded_repo_roots.append(repo_root)
        return repo_root.joinpath("graph.json")

    monkeypatch.setattr(module.cli_self_docs, "get_docs_repo_root", fake_get_docs_repo_root)
    monkeypatch.setattr(module.cli_self_docs, "write_cli_graph_snapshot", fake_write_cli_graph_snapshot)

    module.update_cli_graph()

    assert recorded_repo_roots == [repo_root]


def test_regenerate_charts_uses_sunburst_artifact(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path
    recorded_calls: list[tuple[Path, module.cli_self_docs.DocsArtifactSpec]] = []

    def fake_get_docs_repo_root() -> Path:
        return repo_root

    def fake_render_docs_artifact(*, repo_root: Path, artifact_spec: module.cli_self_docs.DocsArtifactSpec) -> Path:
        recorded_calls.append((repo_root, artifact_spec))
        return repo_root.joinpath(artifact_spec.output_relative_path)

    monkeypatch.setattr(module.cli_self_docs, "get_docs_repo_root", fake_get_docs_repo_root)
    monkeypatch.setattr(module.cli_self_docs, "render_docs_artifact", fake_render_docs_artifact)

    module.regenerate_charts()

    assert recorded_calls == [
        (repo_root, module.cli_self_docs.DocsArtifactSpec(view="sunburst", output_relative_path=module.SUNBURST_OUTPUT_RELATIVE_PATH))
    ]


def test_get_app_invokes_full_and_short_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_update_cli_graph() -> None:
        calls.append("update")

    def fake_regenerate_charts() -> None:
        calls.append("charts")

    monkeypatch.setattr(module, "update_cli_graph", fake_update_cli_graph)
    monkeypatch.setattr(module, "regenerate_charts", fake_regenerate_charts)

    app = module.get_app()

    update_result = RUNNER.invoke(app, ["update-cli-graph"])
    alias_update_result = RUNNER.invoke(app, ["g"])
    chart_result = RUNNER.invoke(app, ["regenerate-charts"])
    alias_chart_result = RUNNER.invoke(app, ["c"])

    assert update_result.exit_code == 0
    assert alias_update_result.exit_code == 0
    assert chart_result.exit_code == 0
    assert alias_chart_result.exit_code == 0
    assert calls == ["update", "update", "charts", "charts"]
