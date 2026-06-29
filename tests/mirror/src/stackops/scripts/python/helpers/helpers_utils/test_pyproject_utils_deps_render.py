from pathlib import Path
import json
import re

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DualDependency,
    DependencyEdge,
    DependencyNode,
    DependencyReport,
)
from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_render import (
    render_dependency_report_html,
)


def test_html_report_embeds_interactive_graph_controls(tmp_path: Path) -> None:
    report = DependencyReport(
        backend="pyan",
        repo_root=tmp_path,
        target_path=tmp_path / "src",
        edge_filter="all",
        nodes=(
            DependencyNode(name="pkg.a", path="src/pkg/a.py"),
            DependencyNode(name="pkg.b", path="src/pkg/b.py"),
        ),
        edges=(
            DependencyEdge(importer="pkg.a", imported="pkg.b"),
            DependencyEdge(importer="pkg.b", imported="pkg.a"),
        ),
        dual_dependencies=(DualDependency(left="pkg.a", right="pkg.b"),),
        cycle_groups=(("pkg.a", "pkg.b"),),
    )

    html = render_dependency_report_html(report)
    json_match = re.search(r'<script type="application/json" id="dependency-report">(?P<payload>.*?)</script>', html, flags=re.S)

    assert 'id="dependency-graph"' in html
    assert 'data-graph-action="move-left"' in html
    assert 'data-graph-action="move-up"' in html
    assert 'data-graph-action="move-down"' in html
    assert 'data-graph-action="move-right"' in html
    assert 'data-graph-action="toggle-cycles"' in html
    assert "&quot;" not in html
    assert json_match is not None
    payload = json.loads(json_match.group("payload"))
    assert payload["edges"] == [
        {"imported": "pkg.b", "importer": "pkg.a"},
        {"imported": "pkg.a", "importer": "pkg.b"},
    ]
