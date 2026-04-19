

from pathlib import Path
import sys
from types import ModuleType
from typing import Protocol, cast

import plotly
import pytest

import stackops.scripts.python.graph.visualize.graph_data as graph_data
import stackops.scripts.python.graph.visualize.plotly_browser as plotly_browser
from stackops.scripts.python.graph.visualize import plotly_views
from stackops.scripts.python.graph.visualize.graph_data import GraphNode
import stackops.utils.code as code_module


class RenderPlotlyFn(Protocol):
    def __call__(
        self,
        *,
        view: str,
        path: str | None,
        output: str | None,
        height: int,
        width: int,
        template: str,
        max_depth: int | None,
    ) -> None: ...


class FakeTrace:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs: dict[str, object] = dict(kwargs)


class FakeFigure:
    created: list["FakeFigure"] = []

    def __init__(self, trace: FakeTrace | None) -> None:
        self.trace = trace
        self.layouts: list[dict[str, object]] = []
        self.show_count = 0
        self.html_writes: list[tuple[Path, str]] = []
        FakeFigure.created.append(self)

    def update_layout(self, **kwargs: object) -> None:
        self.layouts.append(dict(kwargs))

    def show(self) -> None:
        self.show_count += 1

    def write_html(self, output_path: Path, *, include_plotlyjs: str) -> None:
        self.html_writes.append((output_path, include_plotlyjs))


def _build_graph_root() -> GraphNode:
    child = GraphNode(
        id="root child",
        name="child",
        kind="command",
        command="root child",
        description="leaf help",
        long_description="leaf long help",
        aliases=["leaf-alias"],
        depth=1,
        children=[],
        leaf_count=1,
    )
    return GraphNode(
        id="root",
        name="root",
        kind="root",
        command="root",
        description="root help",
        long_description="root long help",
        aliases=[],
        depth=0,
        children=[child],
        leaf_count=1,
    )


def _install_fake_graph_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeFigure.created.clear()
    fake_graph_objects = ModuleType("plotly.graph_objects")
    setattr(fake_graph_objects, "Sunburst", FakeTrace)
    setattr(fake_graph_objects, "Treemap", FakeTrace)
    setattr(fake_graph_objects, "Icicle", FakeTrace)
    setattr(fake_graph_objects, "Figure", FakeFigure)
    monkeypatch.setitem(sys.modules, "plotly.graph_objects", fake_graph_objects)
    monkeypatch.setattr(plotly, "graph_objects", fake_graph_objects, raising=False)


def _render_plotly() -> RenderPlotlyFn:
    return cast(RenderPlotlyFn, getattr(plotly_views, "_render_plotly"))


def test_render_plotly_rejects_unsupported_view(monkeypatch: pytest.MonkeyPatch) -> None:
    root = _build_graph_root()
    render_plotly = _render_plotly()

    def fake_build_graph(path: str | None) -> GraphNode:
        _ = path
        return root

    monkeypatch.setattr(graph_data, "build_graph", fake_build_graph)

    with pytest.raises(ValueError, match="Unsupported view"):
        render_plotly(
            view="radial",
            path=None,
            output=None,
            height=900,
            width=1200,
            template="plotly_dark",
            max_depth=None,
        )


def test_render_plotly_writes_static_image_for_image_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _build_graph_root()
    render_plotly = _render_plotly()
    output_path = tmp_path.joinpath("graph.png")
    image_calls: list[tuple[Path, int, int]] = []

    def fake_build_graph(path: str | None) -> GraphNode:
        _ = path
        return root

    def fake_write_plotly_image(*, fig: object, output: Path, width: int, height: int) -> None:
        _ = fig
        image_calls.append((output, width, height))

    _install_fake_graph_objects(monkeypatch)
    monkeypatch.setattr(graph_data, "build_graph", fake_build_graph)
    monkeypatch.setattr(plotly_browser, "write_plotly_image", fake_write_plotly_image)

    render_plotly(
        view="treemap",
        path=None,
        output=output_path.as_posix(),
        height=410,
        width=510,
        template="plotly_white",
        max_depth=None,
    )

    figure = FakeFigure.created[-1]
    trace = cast(FakeTrace, figure.trace)
    assert image_calls == [(output_path, 510, 410)]
    assert figure.html_writes == []
    assert figure.show_count == 0
    assert cast(list[str], trace.kwargs["labels"]) == ["root", "child"]
    assert cast(list[int], trace.kwargs["values"]) == [1, 1]
    assert f"Wrote {output_path}" in capsys.readouterr().out


def test_render_plotly_writes_html_for_non_image_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _build_graph_root()
    render_plotly = _render_plotly()
    output_path = tmp_path.joinpath("graph.html")

    def fake_build_graph(path: str | None) -> GraphNode:
        _ = path
        return root

    def fail_write_plotly_image(*, fig: object, output: Path, width: int, height: int) -> None:
        _ = fig, output, width, height
        raise AssertionError("write_plotly_image should not be used for HTML output")

    _install_fake_graph_objects(monkeypatch)
    monkeypatch.setattr(graph_data, "build_graph", fake_build_graph)
    monkeypatch.setattr(plotly_browser, "write_plotly_image", fail_write_plotly_image)

    render_plotly(
        view="icicle",
        path=None,
        output=output_path.as_posix(),
        height=300,
        width=400,
        template="plotly_dark",
        max_depth=None,
    )

    figure = FakeFigure.created[-1]
    assert figure.html_writes == [(output_path, "cdn")]
    assert figure.show_count == 0


def test_use_render_plotly_adds_runtime_dependencies_once(monkeypatch: pytest.MonkeyPatch) -> None:
    render_calls: list[tuple[str, str | None, str | None, int, int, str, int | None]] = []
    uv_calls: list[tuple[list[str], str | None]] = []

    def fake_render_plotly(
        *,
        view: str,
        path: str | None,
        output: str | None,
        height: int,
        width: int,
        template: str,
        max_depth: int | None,
    ) -> None:
        render_calls.append((view, path, output, height, width, template, max_depth))

    def fake_run_lambda_function(
        lmb: object,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        uv_run_flags: str = "",
    ) -> None:
        _ = uv_run_flags
        assert callable(lmb)
        assert uv_with is not None
        uv_calls.append((list(uv_with), uv_project_dir))
        lmb()

    monkeypatch.setattr(plotly_views, "_render_plotly", fake_render_plotly)
    monkeypatch.setattr(code_module, "run_lambda_function", fake_run_lambda_function)

    plotly_views.use_render_plotly(
        view="sunburst",
        path="graph.json",
        output="graph.png",
        height=700,
        width=900,
        template="plotly_white",
        max_depth=2,
        uv_with=["plotly"],
        uv_project_dir="/tmp/project",
    )

    assert uv_calls == [(["plotly", "kaleido"], "/tmp/project")]
    assert render_calls == [("sunburst", "graph.json", "graph.png", 700, 900, "plotly_white", 2)]
