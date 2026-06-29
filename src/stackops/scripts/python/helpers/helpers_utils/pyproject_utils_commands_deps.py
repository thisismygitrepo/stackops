from datetime import datetime
from pathlib import Path
import re
from typing import Annotated

import typer

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps import (
    normalize_excludes,
    resolve_dependency_check_context,
    run_backend_dependency_graph,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_graph import (
    filter_dependency_graph_edges,
    find_cycle_groups,
    find_dual_dependencies,
    focus_dependency_graph,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DependencyBackend,
    DependencyEdgeFilter,
    DependencyOutput,
    DependencyRankDirection,
    DependencyReport,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render import (
    render_dependency_report_html,
    report_to_json,
)


def check_deps(
    target: Annotated[
        str,
        typer.Argument(help="Repository root, package directory, or Python file to analyze."),
    ] = ".",
    backend: Annotated[
        DependencyBackend,
        typer.Option("--backend", "-b", help="Dependency analyzer backend."),
    ] = "pyan",
    output: Annotated[
        DependencyOutput,
        typer.Option("--output", "-o", help="Output format: json, jsonic, or html."),
    ] = "json",
    output_path: Annotated[
        str | None,
        typer.Option("--output-path", "-O", help="Write output to this path. Defaults to stdout for JSON and ./.ai/check_deps for HTML."),
    ] = None,
    focus: Annotated[
        list[str] | None,
        typer.Option("--focus", "-f", help="Only keep edges touching this module prefix. Repeat for multiple prefixes."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", "-x", help="Exclude matching files or path parts. Repeat for multiple patterns."),
    ] = None,
    edge_filter: Annotated[
        DependencyEdgeFilter,
        typer.Option("--edge-filter", "-e", help="Edges to show: all, cycles, or direct two-node dual dependencies."),
    ] = "all",
    rankdir: Annotated[
        DependencyRankDirection,
        typer.Option("--rankdir", "-r", help="Graph rank direction used by the backend when applicable."),
    ] = "TB",
) -> None:
    try:
        report = build_dependency_report(
            target=Path(target),
            backend=backend,
            edge_filter=edge_filter,
            rankdir=rankdir,
            focus=tuple(() if focus is None else focus),
            excludes=tuple(() if exclude is None else exclude),
        )
        match output:
            case "json":
                _write_json_output(report=report, output_path=output_path)
            case "jsonic":
                _write_json_output(report=report, output_path=output_path)
            case "html":
                html_path = _write_html_output(report=report, output_path=output_path)
                typer.echo(f"Dependency report written to: {html_path}")
    except (RuntimeError, ValueError) as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(code=1) from error


def build_dependency_report(
    target: Path,
    backend: DependencyBackend,
    edge_filter: DependencyEdgeFilter,
    rankdir: DependencyRankDirection,
    focus: tuple[str, ...],
    excludes: tuple[str, ...],
) -> DependencyReport:
    context = resolve_dependency_check_context(target)
    normalized_excludes = normalize_excludes(excludes)
    graph = run_backend_dependency_graph(
        context=context,
        backend=backend,
        rankdir=rankdir,
        focus=focus,
        excludes=normalized_excludes,
    )
    focused_graph = focus_dependency_graph(graph=graph, focus=focus)
    dual_dependencies = find_dual_dependencies(focused_graph.edges)
    cycle_groups = find_cycle_groups(focused_graph.edges)
    filtered_graph = filter_dependency_graph_edges(graph=focused_graph, edge_filter=edge_filter)
    return DependencyReport(
        backend=backend,
        repo_root=context.repo_root,
        target_path=context.target_path,
        edge_filter=edge_filter,
        nodes=filtered_graph.nodes,
        edges=filtered_graph.edges,
        dual_dependencies=dual_dependencies,
        cycle_groups=cycle_groups,
    )


def _write_json_output(report: DependencyReport, output_path: str | None) -> None:
    payload = report_to_json(report)
    if output_path is None:
        typer.echo(payload, nl=False)
        return
    resolved_output_path = _resolve_output_path(report=report, output_path=output_path, suffix=".json")
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(payload, encoding="utf-8")
    typer.echo(f"Dependency report written to: {resolved_output_path}")


def _write_html_output(report: DependencyReport, output_path: str | None) -> Path:
    resolved_output_path = _resolve_output_path(report=report, output_path=output_path, suffix=".html")
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(render_dependency_report_html(report), encoding="utf-8")
    return resolved_output_path


def _resolve_output_path(report: DependencyReport, output_path: str | None, suffix: str) -> Path:
    if output_path is not None:
        candidate_path = Path(output_path).expanduser()
        if candidate_path.is_absolute() is False:
            candidate_path = report.repo_root / candidate_path
        if candidate_path.suffix == "":
            return candidate_path.with_suffix(suffix)
        return candidate_path
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_slug = _slugify_path(report.target_path)
    return report.repo_root / ".ai" / "check_deps" / f"{timestamp}_{report.backend}_{target_slug}{suffix}"


def _slugify_path(path: Path) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", path.name)
    if slug == "":
        return "target"
    return slug
