

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import polars as pl
import pytest

from stackops.scripts.python.helpers.helpers_repos import repo_analyzer_2 as analyzer_module


@dataclass
class FakeTrace:
    kwargs: dict[str, object]


class FakeFigure:
    def __init__(self) -> None:
        self.traces: list[FakeTrace] = []

    def add_trace(self, trace: FakeTrace) -> None:
        self.traces.append(trace)

    def update_layout(self, **_kwargs: object) -> None:
        return None

    def update_xaxes(self, **_kwargs: object) -> None:
        return None

    def write_html(self, path: Path, include_plotlyjs: str) -> None:
        _ = include_plotlyjs
        Path(path).write_text("html", encoding="utf-8")

    def write_image(self, path: Path, width: int, height: int, scale: int) -> None:
        _ = width, height, scale
        Path(path).write_text("png", encoding="utf-8")


def _install_fake_plotly(monkeypatch: pytest.MonkeyPatch) -> None:
    plotly_module = ModuleType("plotly")
    go_module = ModuleType("plotly.graph_objects")
    px_module = ModuleType("plotly.express")

    setattr(go_module, "Figure", FakeFigure)
    setattr(go_module, "Bar", lambda **kwargs: FakeTrace(kwargs))
    setattr(go_module, "Pie", lambda **kwargs: FakeTrace(kwargs))
    setattr(go_module, "Scatter", lambda **kwargs: FakeTrace(kwargs))
    setattr(px_module, "colors", SimpleNamespace(sequential=SimpleNamespace(Viridis=["#111111", "#222222"])))
    setattr(plotly_module, "graph_objects", go_module)
    setattr(plotly_module, "express", px_module)

    monkeypatch.setitem(sys.modules, "plotly", plotly_module)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", go_module)
    monkeypatch.setitem(sys.modules, "plotly.express", px_module)


def test_print_python_files_by_size_impl_rejects_missing_repo() -> None:
    result = analyzer_module.print_python_files_by_size_impl("/tmp/does-not-exist")

    assert isinstance(result, ValueError)
    assert "does not exist" in str(result)


def test_print_python_files_by_size_impl_ignores_hidden_and_empty_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_plotly(monkeypatch)
    monkeypatch.setattr(analyzer_module.Path, "home", classmethod(lambda cls: tmp_path))

    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    repo_path.joinpath("a.py").write_text("one\n", encoding="utf-8")
    repo_path.joinpath("empty.py").write_text("", encoding="utf-8")
    repo_path.joinpath(".hidden").mkdir()
    repo_path.joinpath(".hidden", "skip.py").write_text("skip\nskip\nskip\n", encoding="utf-8")
    repo_path.joinpath("pkg").mkdir()
    repo_path.joinpath("pkg", "b.py").write_text("1\n2\n3\n", encoding="utf-8")

    result = analyzer_module.print_python_files_by_size_impl(str(repo_path))

    assert isinstance(result, pl.DataFrame)
    assert result["filename"].to_list() == ["pkg/b.py", "a.py"]
    assert result["lines"].to_list() == [3, 1]
    assert tmp_path.joinpath("tmp_results", "tmp_images", "repo", "top_files_by_size.html").is_file()
    assert tmp_path.joinpath("tmp_results", "tmp_images", "repo", "top_files_by_size.png").is_file()


def test_analyze_over_time_writes_visualization_outputs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install_fake_plotly(monkeypatch)
    monkeypatch.setattr(analyzer_module.Path, "home", classmethod(lambda cls: tmp_path))

    commits = [
        SimpleNamespace(hexsha="a1", committed_date=int(datetime(2023, 1, 1, tzinfo=timezone.utc).timestamp())),
        SimpleNamespace(hexsha="b2", committed_date=int(datetime(2023, 6, 1, tzinfo=timezone.utc).timestamp())),
    ]
    repo = SimpleNamespace(iter_commits=lambda branch_name: commits)
    line_counts = {"a1": 10, "b2": 25}

    monkeypatch.setattr(analyzer_module, "Repo", lambda repo_path: repo)
    monkeypatch.setattr(analyzer_module, "get_default_branch", lambda repo: "main")
    monkeypatch.setattr(analyzer_module, "count_python_lines", lambda commit: (line_counts[commit.hexsha], 1))
    import rich.progress

    monkeypatch.setattr(rich.progress, "track", lambda values, description: values)

    analyzer_module.analyze_over_time(str(tmp_path))

    assert tmp_path.joinpath("tmp_results", "tmp_images", tmp_path.name, "code_size_evolution.html").is_file()
    assert tmp_path.joinpath("tmp_results", "tmp_images", tmp_path.name, "code_size_evolution.png").is_file()
