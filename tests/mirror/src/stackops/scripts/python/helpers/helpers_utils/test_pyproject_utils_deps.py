from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import pyproject_utils_app
from stackops.scripts.python.helpers.helpers_utils import pyproject_utils_commands_deps
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_graph import (
    filter_dependency_graph_edges,
    find_cycle_groups,
    find_dual_dependencies,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_parse import (
    parse_pyan_dot,
    parse_pydeps_json,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DualDependency,
    DependencyEdge,
    DependencyGraph,
    DependencyNode,
    DependencyReport,
)


def test_check_deps_command_is_registered() -> None:
    result = CliRunner().invoke(pyproject_utils_app.get_app(), ["check-deps", "--help"])

    assert result.exit_code == 0
    assert "--backend" in result.stdout
    assert "--edge-filter" in result.stdout


def test_parse_pydeps_json_extracts_edges_after_warnings() -> None:
    graph = parse_pydeps_json(
        stdout="""warning: noisy backend line
{
  "pkg.a": {"imports": ["pkg.b"], "path": "/repo/pkg/a.py"},
  "pkg.b": {"imported_by": ["pkg.a"], "imports": ["pkg.a"], "path": "/repo/pkg/b.py"}
}
"""
    )

    assert DependencyNode(name="pkg.a", path="/repo/pkg/a.py") in graph.nodes
    assert DependencyEdge(importer="pkg.a", imported="pkg.b") in graph.edges
    assert DependencyEdge(importer="pkg.b", imported="pkg.a") in graph.edges


def test_parse_pyan_dot_reads_tooltip_module_names() -> None:
    graph = parse_pyan_dot(
        dot_output='''
digraph G {
  "pkg__a" [label="a", tooltip="pkg.a\\nmodule in pkg"];
  "pkg__b" [label="b", tooltip="pkg.b\\nmodule in pkg"];
  "pkg__a" -> "pkg__b" [style="solid"];
}
'''
    )

    assert graph.nodes == (
        DependencyNode(name="pkg.a", path=None),
        DependencyNode(name="pkg.b", path=None),
    )
    assert graph.edges == (DependencyEdge(importer="pkg.a", imported="pkg.b"),)


def test_dual_and_cycle_filters_are_explicit() -> None:
    graph = DependencyGraph(
        nodes=(
            DependencyNode(name="pkg.a", path=None),
            DependencyNode(name="pkg.b", path=None),
            DependencyNode(name="pkg.c", path=None),
        ),
        edges=(
            DependencyEdge(importer="pkg.a", imported="pkg.b"),
            DependencyEdge(importer="pkg.b", imported="pkg.a"),
            DependencyEdge(importer="pkg.b", imported="pkg.c"),
        ),
    )

    assert find_dual_dependencies(graph.edges) == (DualDependency(left="pkg.a", right="pkg.b"),)
    assert find_cycle_groups(graph.edges) == (("pkg.a", "pkg.b"),)
    assert filter_dependency_graph_edges(graph=graph, edge_filter="dual").edges == (
        DependencyEdge(importer="pkg.a", imported="pkg.b"),
        DependencyEdge(importer="pkg.b", imported="pkg.a"),
    )


def test_check_deps_json_output_uses_report_builder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    report = DependencyReport(
        backend="pyan",
        repo_root=tmp_path,
        target_path=tmp_path,
        edge_filter="all",
        nodes=(DependencyNode(name="pkg.a", path=None),),
        edges=(),
        dual_dependencies=(),
        cycle_groups=(),
    )

    def fake_build_dependency_report(
        target: Path,
        backend: str,
        edge_filter: str,
        rankdir: str,
        focus: tuple[str, ...],
        excludes: tuple[str, ...],
    ) -> DependencyReport:
        assert target == Path(".")
        assert backend == "pyan"
        assert edge_filter == "all"
        assert rankdir == "TB"
        assert focus == ()
        assert excludes == ()
        return report

    monkeypatch.setattr(pyproject_utils_commands_deps, "build_dependency_report", fake_build_dependency_report)

    result = CliRunner().invoke(pyproject_utils_app.get_app(), ["check-deps"])

    assert result.exit_code == 0
    assert '"backend": "pyan"' in result.stdout
    assert '"name": "pkg.a"' in result.stdout


def test_backend_runner_uses_uv_with_backend_package(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_runner import (
        run_backend_command,
    )
    from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
        DependencyCheckContext,
    )

    captured_command: list[str] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        capture_output: bool,
        check: bool,
        env: dict[str, str],
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert capture_output is True
        assert check is False
        assert text is True
        assert isinstance(env, dict)
        captured_command.extend(command)
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_backend_command(
        context=DependencyCheckContext(repo_root=tmp_path, target_path=tmp_path),
        backend="pydeps",
        backend_command=["pydeps", "pkg", "--show-deps"],
    )

    assert captured_command[:4] == ["uv", "run", "--with", "pydeps"]
    assert captured_command[4] == "python"
    assert captured_command[-3:] == ["pydeps", "pkg", "--show-deps"]
