from html import escape
import json

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DependencyEdge,
    DependencyNode,
    DependencyReport,
    DualDependency,
    JsonValue,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render_css import (
    DEPENDENCY_REPORT_CSS,
)


def report_to_payload(report: DependencyReport) -> dict[str, JsonValue]:
    return {
        "backend": report.backend,
        "repo_root": report.repo_root.as_posix(),
        "target": report.target_path.as_posix(),
        "edge_filter": report.edge_filter,
        "nodes": [
            {
                "name": node.name,
                "path": node.path,
            }
            for node in report.nodes
        ],
        "edges": [
            {
                "importer": edge.importer,
                "imported": edge.imported,
            }
            for edge in report.edges
        ],
        "dual_dependencies": [
            {
                "left": dependency.left,
                "right": dependency.right,
            }
            for dependency in report.dual_dependencies
        ],
        "cycle_groups": [list(group) for group in report.cycle_groups],
    }


def report_to_json(report: DependencyReport) -> str:
    return json.dumps(report_to_payload(report), indent=2, sort_keys=True) + "\n"


def render_dependency_report_html(report: DependencyReport) -> str:
    payload = report_to_json(report)
    nodes_rows = _render_node_rows(report.nodes)
    edge_rows = _render_edge_rows(report.edges)
    dual_rows = _render_dual_rows(report.dual_dependencies)
    cycle_rows = _render_cycle_rows(report.cycle_groups)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dependency Check</title>
  <style>
{DEPENDENCY_REPORT_CSS}
  </style>
</head>
<body>
<main>
  <h1>Dependency Check</h1>
  <div class="meta">Backend: <code>{escape(report.backend)}</code> - Target: <code>{escape(report.target_path.as_posix())}</code></div>
  <section class="summary">
    <div class="metric"><span>Nodes</span><strong>{len(report.nodes)}</strong></div>
    <div class="metric"><span>Edges</span><strong>{len(report.edges)}</strong></div>
    <div class="metric"><span>Dual Dependencies</span><strong>{len(report.dual_dependencies)}</strong></div>
    <div class="metric"><span>Cycle Groups</span><strong>{len(report.cycle_groups)}</strong></div>
  </section>
  <h2>Direct Mutual Dependencies</h2>
  <table class="danger"><thead><tr><th>Left</th><th>Right</th></tr></thead><tbody>{dual_rows}</tbody></table>
  <h2>Cycle Groups</h2>
  <table class="danger"><thead><tr><th>Modules</th></tr></thead><tbody>{cycle_rows}</tbody></table>
  <h2>Edges</h2>
  <table><thead><tr><th>Importer</th><th>Imported</th></tr></thead><tbody>{edge_rows}</tbody></table>
  <h2>Nodes</h2>
  <table><thead><tr><th>Module</th><th>Path</th></tr></thead><tbody>{nodes_rows}</tbody></table>
  <script type="application/json" id="dependency-report">{escape(payload)}</script>
</main>
</body>
</html>
"""


def _render_node_rows(nodes: tuple[DependencyNode, ...]) -> str:
    if len(nodes) == 0:
        return """<tr><td colspan="2">No nodes.</td></tr>"""
    return "".join(
        f"""<tr><td><code>{escape(node.name)}</code></td><td><code>{escape(node.path or "")}</code></td></tr>"""
        for node in nodes
    )


def _render_edge_rows(edges: tuple[DependencyEdge, ...]) -> str:
    if len(edges) == 0:
        return """<tr><td colspan="2">No edges.</td></tr>"""
    return "".join(
        f"""<tr><td><code>{escape(edge.importer)}</code></td><td><code>{escape(edge.imported)}</code></td></tr>"""
        for edge in edges
    )


def _render_dual_rows(dual_dependencies: tuple[DualDependency, ...]) -> str:
    if len(dual_dependencies) == 0:
        return """<tr><td colspan="2">No direct mutual dependencies.</td></tr>"""
    return "".join(
        f"""<tr><td><code>{escape(dependency.left)}</code></td><td><code>{escape(dependency.right)}</code></td></tr>"""
        for dependency in dual_dependencies
    )


def _render_cycle_rows(cycle_groups: tuple[tuple[str, ...], ...]) -> str:
    if len(cycle_groups) == 0:
        return """<tr><td>No cycles.</td></tr>"""
    return "".join(
        f"""<tr><td>{", ".join(f"<code>{escape(module)}</code>" for module in group)}</td></tr>"""
        for group in cycle_groups
    )
