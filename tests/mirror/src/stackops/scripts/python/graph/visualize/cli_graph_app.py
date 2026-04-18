from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import sys
from types import ModuleType
from typing import cast

import pytest
from _pytest.monkeypatch import MonkeyPatch
from click.core import Group
from typer.main import get_command
import typer

import stackops.scripts.python.graph.visualize.cli_graph_app as target


type ShellLambda = Callable[[], None]
type LambdaRunner = Callable[[ShellLambda, list[str] | None, str | None], tuple[Path, Path]]
type ExitRunner = Callable[[str, bool], None]


@dataclass(frozen=True)
class ShellExitCall:
    script: str
    strict: bool


def _install_shell_dependencies(
    monkeypatch: MonkeyPatch,
    *,
    lambda_runner: LambdaRunner,
    exit_runner: ExitRunner,
) -> None:
    abc_module = ModuleType("stackops.utils.ssh_utils.abc")
    code_module = ModuleType("stackops.utils.code")

    setattr(abc_module, "STACKOPS_VERSION", "stackops")
    setattr(
        code_module,
        "get_shell_script_running_lambda_function",
        lambda_runner,
    )
    setattr(code_module, "exit_then_run_shell_script", exit_runner)
    monkeypatch.setitem(sys.modules, abc_module.__name__, abc_module)
    monkeypatch.setitem(sys.modules, code_module.__name__, code_module)


def test_get_app_registers_public_commands_and_hidden_aliases() -> None:
    command = cast(Group, get_command(target.get_app()))

    assert set(command.commands) == {
        "search",
        "s",
        "tree",
        "t",
        "dot",
        "d",
        "view",
        "v",
        "tui",
        "u",
    }
    assert command.commands["search"].hidden is False
    assert command.commands["s"].hidden is True
    assert command.commands["tree"].hidden is False
    assert command.commands["t"].hidden is True


def test_tree_runs_render_tree_inside_shell_wrapper(
    monkeypatch: MonkeyPatch,
) -> None:
    render_calls: list[tuple[bool, bool, int | None]] = []
    shell_calls: list[tuple[list[str] | None, str | None]] = []
    exit_calls: list[ShellExitCall] = []
    project_dir = str(Path.home().joinpath("code", "stackops"))

    rich_tree_module = ModuleType(
        "stackops.scripts.python.graph.visualize.rich_tree"
    )

    def render_tree(
        *,
        show_help: bool,
        show_aliases: bool,
        max_depth: int | None,
    ) -> None:
        render_calls.append((show_help, show_aliases, max_depth))

    def lambda_runner(
        fn: ShellLambda,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
    ) -> tuple[Path, Path]:
        shell_calls.append((uv_with, uv_project_dir))
        fn()
        return Path("/tmp/tree.sh"), Path("/tmp/tree.py")

    def exit_runner(script: str, strict: bool) -> None:
        exit_calls.append(ShellExitCall(script=script, strict=strict))

    setattr(rich_tree_module, "render_tree", render_tree)
    monkeypatch.setitem(sys.modules, rich_tree_module.__name__, rich_tree_module)
    _install_shell_dependencies(
        monkeypatch,
        lambda_runner=lambda_runner,
        exit_runner=exit_runner,
    )

    target.tree(show_help=False, show_aliases=True, max_depth=2)

    assert render_calls == [(False, True, 2)]
    assert shell_calls == [(["plotly", "kaleido"], project_dir)]
    assert exit_calls == [ShellExitCall(script="/tmp/tree.sh", strict=False)]


def test_dot_writes_output_inside_shell_wrapper(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    render_calls: list[tuple[int | None, bool]] = []
    shell_calls: list[tuple[list[str] | None, str | None]] = []
    exit_calls: list[ShellExitCall] = []
    output_path = tmp_path / "graph.dot"
    project_dir = str(Path.home().joinpath("code", "stackops"))

    dot_export_module = ModuleType(
        "stackops.scripts.python.graph.visualize.dot_export"
    )

    def render_dot(*, max_depth: int | None, include_help: bool) -> str:
        render_calls.append((max_depth, include_help))
        return "digraph { a -> b }"

    def lambda_runner(
        fn: ShellLambda,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
    ) -> tuple[Path, Path]:
        shell_calls.append((uv_with, uv_project_dir))
        fn()
        return Path("/tmp/dot.sh"), Path("/tmp/dot.py")

    def exit_runner(script: str, strict: bool) -> None:
        exit_calls.append(ShellExitCall(script=script, strict=strict))

    setattr(dot_export_module, "render_dot", render_dot)
    monkeypatch.setitem(sys.modules, dot_export_module.__name__, dot_export_module)
    _install_shell_dependencies(
        monkeypatch,
        lambda_runner=lambda_runner,
        exit_runner=exit_runner,
    )

    target.dot(output=output_path, include_help=False, max_depth=4)

    assert render_calls == [(4, False)]
    assert output_path.read_text(encoding="utf-8") == "digraph { a -> b }"
    assert shell_calls == [(["plotly", "kaleido"], project_dir)]
    assert exit_calls == [ShellExitCall(script="/tmp/dot.sh", strict=False)]


def test_chart_uses_render_plotly_with_local_project(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    seen_calls: list[dict[str, object]] = []
    plotly_views_module = ModuleType(
        "stackops.scripts.python.graph.visualize.plotly_views"
    )
    abc_module = ModuleType("stackops.utils.ssh_utils.abc")
    project_dir = str(Path.home().joinpath("code/stackops"))

    def use_render_plotly(
        *,
        view: str,
        output: str | None,
        height: int,
        width: int,
        template: str,
        max_depth: int | None,
        path: str | None,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
    ) -> None:
        seen_calls.append(
            {
                "view": view,
                "output": output,
                "height": height,
                "width": width,
                "template": template,
                "max_depth": max_depth,
                "path": path,
                "uv_with": uv_with,
                "uv_project_dir": uv_project_dir,
            }
        )

    setattr(abc_module, "STACKOPS_VERSION", "stackops")
    setattr(plotly_views_module, "use_render_plotly", use_render_plotly)
    monkeypatch.setitem(sys.modules, abc_module.__name__, abc_module)
    monkeypatch.setitem(sys.modules, plotly_views_module.__name__, plotly_views_module)

    output_path = tmp_path / "chart.html"
    target.chart(
        view="treemap",
        output=output_path,
        max_depth=3,
        template="plotly_white",
        height=700,
        width=1100,
    )

    assert seen_calls == [
        {
            "view": "treemap",
            "output": str(output_path),
            "height": 700,
            "width": 1100,
            "template": "plotly_white",
            "max_depth": 3,
            "path": None,
            "uv_with": None,
            "uv_project_dir": project_dir,
        }
    ]


def test_search_raises_typer_exit_for_non_zero_result(
    monkeypatch: MonkeyPatch,
) -> None:
    search_calls: list[tuple[Path, bool]] = []
    shell_calls: list[tuple[list[str] | None, str | None]] = []
    graph_path = Path("/tmp/cli_graph.json")
    project_dir = str(Path.home().joinpath("code", "stackops"))

    graph_paths_module = ModuleType(
        "stackops.scripts.python.graph.visualize.graph_paths"
    )
    search_module = ModuleType(
        "stackops.scripts.python.graph.visualize.cli_graph_search"
    )

    def search_cli_graph(*, graph_path: Path, show_json: bool) -> int:
        search_calls.append((graph_path, show_json))
        return 3

    def lambda_runner(
        fn: ShellLambda,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
    ) -> tuple[Path, Path]:
        shell_calls.append((uv_with, uv_project_dir))
        fn()
        return Path("/tmp/search.sh"), Path("/tmp/search.py")

    def exit_runner(script: str, strict: bool) -> None:
        _ = (script, strict)

    setattr(graph_paths_module, "DEFAULT_GRAPH_PATH", graph_path)
    setattr(search_module, "search_cli_graph", search_cli_graph)
    monkeypatch.setitem(sys.modules, graph_paths_module.__name__, graph_paths_module)
    monkeypatch.setitem(sys.modules, search_module.__name__, search_module)
    _install_shell_dependencies(
        monkeypatch,
        lambda_runner=lambda_runner,
        exit_runner=exit_runner,
    )

    with pytest.raises(typer.Exit) as exc_info:
        target.search(graph_path=None, show_json=True)

    assert exc_info.value.exit_code == 3
    assert search_calls == [(graph_path, True)]
    assert shell_calls == [([], project_dir)]


def test_navigate_runs_devops_navigator_in_shell_wrapper(
    monkeypatch: MonkeyPatch,
) -> None:
    navigator_calls: list[str] = []
    shell_calls: list[tuple[list[str] | None, str | None]] = []
    exit_calls: list[ShellExitCall] = []
    project_dir = str(Path.home().joinpath("code/stackops"))

    navigator_module = ModuleType(
        "stackops.scripts.python.graph.visualize.helpers_navigator.devops_navigator"
    )

    def main() -> None:
        navigator_calls.append("main")

    def lambda_runner(
        fn: ShellLambda,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
    ) -> tuple[Path, Path]:
        shell_calls.append((uv_with, uv_project_dir))
        fn()
        return Path("/tmp/navigate.sh"), Path("/tmp/navigate.py")

    def exit_runner(script: str, strict: bool) -> None:
        exit_calls.append(ShellExitCall(script=script, strict=strict))

    setattr(navigator_module, "main", main)
    monkeypatch.setitem(sys.modules, navigator_module.__name__, navigator_module)
    _install_shell_dependencies(
        monkeypatch,
        lambda_runner=lambda_runner,
        exit_runner=exit_runner,
    )

    target.navigate()

    assert navigator_calls == ["main"]
    assert shell_calls == [(["textual"], project_dir)]
    assert exit_calls == [ShellExitCall(script="/tmp/navigate.sh", strict=False)]
