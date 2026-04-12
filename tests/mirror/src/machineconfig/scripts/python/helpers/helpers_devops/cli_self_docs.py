from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_devops import cli_self_docs as module


def test_get_docs_repo_root_returns_repo_when_sources_exist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import machineconfig.utils.source_of_truth as source_of_truth

    tmp_path.joinpath("docs").mkdir()
    tmp_path.joinpath(module.DOCS_CONFIG_FILE_NAME).write_text("", encoding="utf-8")
    monkeypatch.setattr(source_of_truth, "REPO_ROOT", tmp_path)

    assert module.get_docs_repo_root() == tmp_path


def test_get_docs_repo_root_exits_when_sources_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import machineconfig.utils.source_of_truth as source_of_truth

    monkeypatch.setattr(source_of_truth, "REPO_ROOT", tmp_path)

    with pytest.raises(typer.Exit) as exc_info:
        module.get_docs_repo_root()

    captured = capsys.readouterr()
    assert exc_info.value.exit_code == 1
    assert "Could not find docs sources" in captured.err


def test_write_cli_graph_snapshot_writes_json_payload(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    generated_module = ModuleType("machineconfig.scripts.python.graph.generate_cli_graph")
    tmp_path.joinpath("generated").mkdir()

    def fake_build_cli_graph() -> dict[str, object]:
        return {"commands": ["status"]}

    setattr(generated_module, "build_cli_graph", fake_build_cli_graph)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.graph.generate_cli_graph", generated_module)
    monkeypatch.setattr(module, "CLI_GRAPH_RELATIVE_PATH", Path("generated/cli_graph.json"))

    output_path = module.write_cli_graph_snapshot(repo_root=tmp_path)

    assert output_path == tmp_path.joinpath("generated/cli_graph.json")
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"commands": ["status"]}
    assert "generated/cli_graph.json" in capsys.readouterr().out


def test_render_docs_artifact_creates_parent_and_calls_plotly(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plotly_views_module = ModuleType("machineconfig.scripts.python.graph.visualize.plotly_views")
    recorded_calls: list[dict[str, object]] = []

    def fake_use_render_plotly(
        *, view: str, output: str, template: str, path: str | None, max_depth: int | None, uv_with: str | None, uv_project_dir: str | None
    ) -> None:
        recorded_calls.append(
            {
                "view": view,
                "output": output,
                "template": template,
                "path": path,
                "max_depth": max_depth,
                "uv_with": uv_with,
                "uv_project_dir": uv_project_dir,
            }
        )

    setattr(plotly_views_module, "use_render_plotly", fake_use_render_plotly)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.graph.visualize.plotly_views", plotly_views_module)

    artifact_spec = module.DocsArtifactSpec(view="sunburst", output_relative_path=Path("docs/assets/chart.html"))

    output_path = module.render_docs_artifact(repo_root=tmp_path, artifact_spec=artifact_spec)

    assert output_path == tmp_path.joinpath("docs/assets/chart.html")
    assert output_path.parent.is_dir()
    assert recorded_calls == [
        {
            "view": "sunburst",
            "output": str(output_path),
            "template": module.DOCS_ARTIFACT_TEMPLATE,
            "path": None,
            "max_depth": None,
            "uv_with": None,
            "uv_project_dir": None,
        }
    ]
    assert "docs/assets/chart.html" in capsys.readouterr().out


def test_serve_docs_builds_expected_shell_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import machineconfig.utils.code as code_utils
    import platform

    recorded_scripts: list[tuple[str, bool]] = []
    created_artifacts_for: list[Path] = []

    def fake_get_docs_repo_root() -> Path:
        return tmp_path

    def fake_print_docs_urls() -> None:
        return None

    def fake_create_docs_artifacts(*, repo_root: Path) -> list[Path]:
        created_artifacts_for.append(repo_root)
        return [repo_root.joinpath("docs/assets/chart.html")]

    def fake_get_uv_command(*, platform: str) -> str:
        assert platform == "Linux"
        return "uv"

    def fake_exit_then_run_shell_script(*, script: str, strict: bool) -> None:
        recorded_scripts.append((script, strict))

    monkeypatch.setattr(module, "get_docs_repo_root", fake_get_docs_repo_root)
    monkeypatch.setattr(module, "_print_docs_urls", fake_print_docs_urls)
    monkeypatch.setattr(module, "create_docs_artifacts", fake_create_docs_artifacts)
    monkeypatch.setattr(code_utils, "get_uv_command", fake_get_uv_command)
    monkeypatch.setattr(code_utils, "exit_then_run_shell_script", fake_exit_then_run_shell_script)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    module.serve_docs(rebuild=True, create_artifacts=True)

    assert created_artifacts_for == [tmp_path]
    assert recorded_scripts == [
        (
            f"""
cd \"{tmp_path}\"
uv run zensical build
uv run zensical serve -a {module.DOCS_BIND_ADDRESS}:{module.DOCS_PORT}
""",
            False,
        )
    ]
