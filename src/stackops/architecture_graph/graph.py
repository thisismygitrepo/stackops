from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from stackops.architecture_graph.models import (
    EdgePayload,
    GraphPagePayload,
    GraphPayload,
    InternalImport,
    NodeId,
    NodePayload,
    PythonModule,
)
from stackops.architecture_graph.scanner import collect_internal_imports, discover_python_modules


def build_graph_page_payload(
    source_root: Path,
    package_name: str,
    initial_depth: int,
    max_depth: int,
) -> GraphPagePayload:
    if initial_depth < 0:
        raise ValueError("initial_depth must be zero or greater")
    if max_depth < initial_depth:
        raise ValueError("max_depth must be greater than or equal to initial_depth")
    modules = discover_python_modules(source_root=source_root, package_name=package_name)
    imports = collect_internal_imports(modules=modules, package_name=package_name)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    depths = {
        str(depth): graph_payload_from_imports(
            source_root=source_root,
            package_name=package_name,
            depth=depth,
            generated_at=generated_at,
            modules=modules,
            imports=imports,
        )
        for depth in range(max_depth + 1)
    }
    return {
        "packageName": package_name,
        "sourceRoot": str(source_root),
        "generatedAt": generated_at,
        "initialDepth": initial_depth,
        "maxDepth": max_depth,
        "depths": depths,
    }


def build_graph_payload(source_root: Path, package_name: str, depth: int) -> GraphPayload:
    if depth < 0:
        raise ValueError("depth must be zero or greater")
    modules = discover_python_modules(source_root=source_root, package_name=package_name)
    imports = collect_internal_imports(modules=modules, package_name=package_name)
    generated_at = datetime.now(UTC).isoformat(timespec="seconds")
    return graph_payload_from_imports(
        source_root=source_root,
        package_name=package_name,
        depth=depth,
        generated_at=generated_at,
        modules=modules,
        imports=imports,
    )


def graph_payload_from_imports(
    source_root: Path,
    package_name: str,
    depth: int,
    generated_at: str,
    modules: list[PythonModule],
    imports: list[InternalImport],
) -> GraphPayload:
    module_nodes = {
        module.name: aggregate_module_name(module.name, package_name, depth)
        for module in modules
    }
    node_module_counts: Counter[NodeId] = Counter(module_nodes.values())
    node_file_counts: Counter[NodeId] = Counter(module_nodes[module.name] for module in modules)
    edge_counts: Counter[tuple[NodeId, NodeId]] = Counter()

    for internal_import in imports:
        source = module_nodes[internal_import.importer]
        target = module_nodes[internal_import.imported]
        if source != target:
            edge_counts[(source, target)] += 1

    return {
        "packageName": package_name,
        "sourceRoot": str(source_root),
        "depth": depth,
        "generatedAt": generated_at,
        "moduleCount": len(modules),
        "importCount": len(imports),
        "nodes": node_payloads(node_module_counts, node_file_counts, package_name),
        "edges": edge_payloads(edge_counts),
    }


def aggregate_module_name(module_name: str, package_name: str, depth: int) -> NodeId:
    package_parts = package_name.split(".")
    module_parts = module_name.split(".")
    keep_count = len(package_parts) + depth
    if len(module_parts) <= keep_count:
        return module_name
    return ".".join(module_parts[:keep_count])


def node_payloads(
    module_counts: Counter[NodeId],
    file_counts: Counter[NodeId],
    package_name: str,
) -> list[NodePayload]:
    return [
        {
            "id": node_id,
            "label": node_label(node_id, package_name),
            "group": node_group(node_id, package_name),
            "moduleCount": module_counts[node_id],
            "fileCount": file_counts[node_id],
        }
        for node_id in sorted(module_counts)
    ]


def edge_payloads(edge_counts: Counter[tuple[NodeId, NodeId]]) -> list[EdgePayload]:
    return [
        {"source": source, "target": target, "count": count}
        for (source, target), count in sorted(edge_counts.items())
    ]


def node_label(node_id: NodeId, package_name: str) -> str:
    if node_id == package_name:
        return package_name
    suffix = node_id.removeprefix(f"{package_name}.")
    suffix_parts = suffix.split(".")
    if len(suffix_parts) == 1:
        return suffix
    return "/".join(suffix_parts[-2:])


def node_group(node_id: NodeId, package_name: str) -> str:
    if node_id == package_name:
        return package_name
    suffix = node_id.removeprefix(f"{package_name}.")
    return suffix.split(".")[0]
