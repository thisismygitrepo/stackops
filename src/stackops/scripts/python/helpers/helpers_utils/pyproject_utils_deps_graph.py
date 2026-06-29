from collections.abc import Iterable

from stackops.scripts.python.helpers.helpers_utils.pyproject_utils_deps_models import (
    DependencyEdge,
    DependencyEdgeFilter,
    DependencyGraph,
    DualDependency,
)


def focus_dependency_graph(graph: DependencyGraph, focus: tuple[str, ...]) -> DependencyGraph:
    if len(focus) == 0:
        return graph
    edges = tuple(
        edge
        for edge in graph.edges
        if _matches_focus(module_name=edge.importer, focus=focus) or _matches_focus(module_name=edge.imported, focus=focus)
    )
    node_names = edge_node_names(edges)
    nodes = tuple(node for node in graph.nodes if node.name in node_names)
    return DependencyGraph(nodes=nodes, edges=edges)


def filter_dependency_graph_edges(graph: DependencyGraph, edge_filter: DependencyEdgeFilter) -> DependencyGraph:
    match edge_filter:
        case "all":
            return graph
        case "cycles":
            cycle_node_groups = find_cycle_groups(graph.edges)
            cycle_nodes = {node_name for group in cycle_node_groups for node_name in group}
            edges = tuple(edge for edge in graph.edges if edge.importer in cycle_nodes and edge.imported in cycle_nodes)
        case "dual":
            dual_dependencies = find_dual_dependencies(graph.edges)
            dual_edges = {
                DependencyEdge(importer=dependency.left, imported=dependency.right)
                for dependency in dual_dependencies
            } | {
                DependencyEdge(importer=dependency.right, imported=dependency.left)
                for dependency in dual_dependencies
            }
            edges = tuple(edge for edge in graph.edges if edge in dual_edges)
    node_names = edge_node_names(edges)
    nodes = tuple(node for node in graph.nodes if node.name in node_names)
    return DependencyGraph(nodes=nodes, edges=edges)


def find_dual_dependencies(edges: tuple[DependencyEdge, ...]) -> tuple[DualDependency, ...]:
    edge_pairs = {(edge.importer, edge.imported) for edge in edges}
    dual_dependencies: set[DualDependency] = set()
    for importer, imported in edge_pairs:
        if importer == imported:
            continue
        if (imported, importer) in edge_pairs:
            left, right = sorted((importer, imported))
            dual_dependencies.add(DualDependency(left=left, right=right))
    return tuple(sorted(dual_dependencies))


def find_cycle_groups(edges: tuple[DependencyEdge, ...]) -> tuple[tuple[str, ...], ...]:
    nodes = sorted(edge_node_names(edges))
    adjacency: dict[str, tuple[str, ...]] = {
        node: tuple(sorted(edge.imported for edge in edges if edge.importer == node))
        for node in nodes
    }
    index_by_node: dict[str, int] = {}
    lowlink_by_node: dict[str, int] = {}
    stack: list[str] = []
    stack_members: set[str] = set()
    groups: list[tuple[str, ...]] = []
    next_index = 0

    def visit(node: str) -> None:
        nonlocal next_index
        index_by_node[node] = next_index
        lowlink_by_node[node] = next_index
        next_index += 1
        stack.append(node)
        stack_members.add(node)
        for imported in adjacency.get(node, ()):
            if imported not in index_by_node:
                visit(imported)
                lowlink_by_node[node] = min(lowlink_by_node[node], lowlink_by_node[imported])
            elif imported in stack_members:
                lowlink_by_node[node] = min(lowlink_by_node[node], index_by_node[imported])
        if lowlink_by_node[node] != index_by_node[node]:
            return
        component: list[str] = []
        while len(stack) > 0:
            member = stack.pop()
            stack_members.remove(member)
            component.append(member)
            if member == node:
                break
        component_sorted = tuple(sorted(component))
        has_self_loop = any(edge.importer == node and edge.imported == node for edge in edges)
        if len(component_sorted) > 1 or has_self_loop:
            groups.append(component_sorted)

    for node in nodes:
        if node not in index_by_node:
            visit(node)
    return tuple(sorted(groups))


def edge_node_names(edges: Iterable[DependencyEdge]) -> set[str]:
    node_names: set[str] = set()
    for edge in edges:
        node_names.add(edge.importer)
        node_names.add(edge.imported)
    return node_names


def _matches_focus(module_name: str, focus: tuple[str, ...]) -> bool:
    return any(module_name == focus_module or module_name.startswith(f"{focus_module}.") for focus_module in focus)
