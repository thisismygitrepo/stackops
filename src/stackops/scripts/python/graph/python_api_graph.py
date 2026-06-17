import ast
import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_ROOT = REPO_ROOT / "src"
DOCS_API_ROOT = REPO_ROOT / "docs" / "api"

DOCS_DIRECTIVE_RE = re.compile(r"^:{3,4}\s+([A-Za-z_][\w.]*)(?:\s|$)")
FROM_IMPORT_RE = re.compile(r"^\s*from\s+(stackops(?:\.[A-Za-z_][\w]*)*)\s+import\s+(.+)$")
IMPORT_RE = re.compile(r"^\s*import\s+(stackops(?:\.[A-Za-z_][\w]*)*)")

EXCLUDED_PUBLIC_NAMES = {
    "app",
    "cli_app",
    "get_app",
    "main",
}


@dataclass
class ApiModuleSelection:
    module: str
    path: Path
    include_all: bool = False
    explicit_names: set[str] = field(default_factory=set)
    docs_pages: set[str] = field(default_factory=set)


def build_python_api_graph(*, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    selections = collect_api_module_selections(repo_root=root)

    root_node: dict[str, Any] = {
        "kind": "root",
        "name": "stackops",
        "qualified_name": "stackops",
        "fullPath": "stackops",
        "help": "StackOps Python API",
        "doc": (
            "Docs-driven Python API graph. Modules come from docs/api mkdocstrings "
            "directives and explicit docs import examples; members are public AST "
            "symbols only."
        ),
        "children": [],
    }

    package_nodes: dict[str, dict[str, Any]] = {"stackops": root_node}
    for selection in sorted(selections.values(), key=lambda item: item.module):
        module_node = _build_module_node(selection=selection, repo_root=root)
        _insert_module_node(root_node=root_node, package_nodes=package_nodes, module_node=module_node)

    _sort_children(root_node)
    return {
        "schema": {
            "version": "1.0",
            "description": "Hierarchical graph of the documented StackOps Python API.",
            "node": {
                "kind": "root | package | module | class | function | async-function | method | constant | export",
                "name": "Display name for the node",
                "qualified_name": "Dotted import path for the node",
                "help": "Short description derived from the docstring or value summary",
                "doc": "Full docstring where available",
                "source": "Source file, module, object, line number, and docs pages",
                "signature": "Simple AST signature text for callable nodes",
                "children": "Nested packages, modules, class methods, and module members",
            },
        },
        "meta": {
            "source": "docs/api + AST",
            "repo_root": str(root),
            "rules": [
                "Only modules referenced by docs/api mkdocstrings directives or explicit docs imports are included.",
                "Wildcard prose mentions are not expanded automatically.",
                "Top-level public classes, functions, async functions, and constants are included.",
                "Private names and common CLI command wiring names are excluded.",
                "If a module defines __all__, it narrows include-all member selection to exported names.",
            ],
            "module_count": len(selections),
        },
        "root": root_node,
    }


def collect_api_module_selections(*, repo_root: Path | None = None) -> dict[str, ApiModuleSelection]:
    root = repo_root or REPO_ROOT
    docs_root = root / "docs" / "api"
    src_root = root / "src"
    selections: dict[str, ApiModuleSelection] = {}

    if not docs_root.is_dir():
        return selections

    for docs_path in sorted(docs_root.rglob("*.md")):
        relative_docs_path = docs_path.relative_to(root).as_posix()
        text = docs_path.read_text(encoding="utf-8")
        for target in _iter_docs_targets(text):
            resolved = _resolve_target(target=target, src_root=src_root)
            if resolved is None:
                continue
            module, path, object_name = resolved
            selection = selections.setdefault(module, ApiModuleSelection(module=module, path=path))
            selection.docs_pages.add(relative_docs_path)
            if object_name:
                selection.explicit_names.add(object_name.split(".", 1)[0])
            else:
                selection.include_all = True

    return selections


def write_python_api_graph_json(*, output: Path, repo_root: Path | None = None) -> Path:
    payload = build_python_api_graph(repo_root=repo_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output


def write_python_api_graph_temp(*, repo_root: Path | None = None) -> Path:
    temp_dir = Path(tempfile.mkdtemp(prefix="stackops-python-api-graph-"))
    return write_python_api_graph_json(output=temp_dir / "python_api_graph.json", repo_root=repo_root)


def _iter_docs_targets(text: str) -> list[str]:
    targets: list[str] = []
    for line in text.splitlines():
        directive_match = DOCS_DIRECTIVE_RE.match(line)
        if directive_match is not None:
            targets.append(directive_match.group(1))
            continue

        from_match = FROM_IMPORT_RE.match(line)
        if from_match is not None:
            module = from_match.group(1)
            imported_names = _parse_imported_names(from_match.group(2))
            if imported_names:
                targets.extend(f"{module}.{name}" for name in imported_names)
            else:
                targets.append(module)
            continue

        import_match = IMPORT_RE.match(line)
        if import_match is not None:
            targets.append(import_match.group(1))

    return targets


def _parse_imported_names(value: str) -> list[str]:
    stripped = value.strip()
    if not stripped or stripped.startswith("("):
        return []
    names: list[str] = []
    for part in stripped.split(","):
        name = part.strip().split(" as ", 1)[0].strip()
        if not name or name == "*":
            return []
        if re.match(r"^[A-Za-z_]\w*$", name):
            names.append(name)
    return names


def _resolve_target(*, target: str, src_root: Path) -> tuple[str, Path, str | None] | None:
    if not target.startswith("stackops"):
        return None

    parts = target.split(".")
    for index in range(len(parts), 0, -1):
        module = ".".join(parts[:index])
        path = _module_path(module=module, src_root=src_root)
        if path is None:
            continue
        object_name = ".".join(parts[index:]) or None
        return module, path, object_name
    return None


def _module_path(*, module: str, src_root: Path) -> Path | None:
    parts = module.split(".")
    if not parts or parts[0] != "stackops":
        return None
    relative = Path(*parts)
    file_path = src_root / relative.with_suffix(".py")
    if file_path.is_file():
        return file_path
    package_path = src_root / relative / "__init__.py"
    if package_path.is_file():
        return package_path
    return None


def _build_module_node(*, selection: ApiModuleSelection, repo_root: Path) -> dict[str, Any]:
    source = selection.path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(selection.path))
    module_doc = ast.get_docstring(tree) or ""
    source_file = selection.path.relative_to(repo_root).as_posix()
    docs_pages = sorted(selection.docs_pages)
    exported_names = _module_all(tree)

    module_node: dict[str, Any] = {
        "kind": "package" if selection.path.name == "__init__.py" else "module",
        "name": selection.module.rsplit(".", 1)[-1],
        "qualified_name": selection.module,
        "fullPath": selection.module,
        "help": _summary(module_doc) or selection.module,
        "doc": module_doc,
        "source": {
            "file": source_file,
            "module": selection.module,
            "docs_pages": docs_pages,
        },
        "children": _module_members(
            tree=tree,
            module=selection.module,
            source_file=source_file,
            docs_pages=docs_pages,
            include_all=selection.include_all,
            explicit_names=selection.explicit_names,
            exported_names=exported_names,
        ),
    }
    return module_node


def _module_members(
    *,
    tree: ast.Module,
    module: str,
    source_file: str,
    docs_pages: list[str],
    include_all: bool,
    explicit_names: set[str],
    exported_names: set[str] | None,
) -> list[dict[str, Any]]:
    members: list[dict[str, Any]] = []
    exported_or_explicit = set(explicit_names)
    if exported_names is not None:
        exported_or_explicit.update(exported_names)

    for node in tree.body:
        name = _node_name(node)
        if name is None or not _include_member(name=name, include_all=include_all, explicit_names=exported_or_explicit, exported_names=exported_names):
            continue

        if isinstance(node, ast.ClassDef):
            members.append(_class_node(node=node, module=module, source_file=source_file, docs_pages=docs_pages))
        elif isinstance(node, ast.AsyncFunctionDef):
            members.append(_function_node(node=node, module=module, source_file=source_file, docs_pages=docs_pages, kind="async-function"))
        elif isinstance(node, ast.FunctionDef):
            members.append(_function_node(node=node, module=module, source_file=source_file, docs_pages=docs_pages, kind="function"))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            constant_node = _constant_node(node=node, name=name, module=module, source_file=source_file, docs_pages=docs_pages)
            if constant_node is not None:
                members.append(constant_node)

    return sorted(members, key=lambda item: (_kind_sort_key(str(item.get("kind"))), str(item.get("name"))))


def _include_member(*, name: str, include_all: bool, explicit_names: set[str], exported_names: set[str] | None) -> bool:
    if name.startswith("_"):
        return name in explicit_names
    if name in EXCLUDED_PUBLIC_NAMES and name not in explicit_names:
        return False
    if name in explicit_names:
        return True
    if exported_names is not None:
        return include_all and name in exported_names
    return include_all


def _class_node(*, node: ast.ClassDef, module: str, source_file: str, docs_pages: list[str]) -> dict[str, Any]:
    qualified_name = f"{module}.{node.name}"
    doc = ast.get_docstring(node) or ""
    return {
        "kind": "class",
        "name": node.name,
        "qualified_name": qualified_name,
        "fullPath": qualified_name,
        "help": _summary(doc) or node.name,
        "doc": doc,
        "signature": _class_signature(node),
        "source": _source(source_file=source_file, module=module, object_name=node.name, line=node.lineno, docs_pages=docs_pages),
        "children": _class_methods(node=node, module=module, source_file=source_file, docs_pages=docs_pages),
    }


def _class_methods(*, node: ast.ClassDef, module: str, source_file: str, docs_pages: list[str]) -> list[dict[str, Any]]:
    methods: list[dict[str, Any]] = []
    for item in node.body:
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if item.name.startswith("_"):
            continue
        methods.append(
            _function_node(
                node=item,
                module=f"{module}.{node.name}",
                source_file=source_file,
                docs_pages=docs_pages,
                kind="method",
            )
        )
    return sorted(methods, key=lambda item: str(item.get("name")))


def _function_node(
    *,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    module: str,
    source_file: str,
    docs_pages: list[str],
    kind: str,
) -> dict[str, Any]:
    qualified_name = f"{module}.{node.name}"
    doc = ast.get_docstring(node) or ""
    return {
        "kind": kind,
        "name": node.name,
        "qualified_name": qualified_name,
        "fullPath": qualified_name,
        "help": _summary(doc) or node.name,
        "doc": doc,
        "signature": {"text": _signature_text(node)},
        "source": _source(source_file=source_file, module=module.rsplit(".", 1)[0] if kind == "method" else module, object_name=node.name, line=node.lineno, docs_pages=docs_pages),
    }


def _constant_node(
    *,
    node: ast.Assign | ast.AnnAssign,
    name: str,
    module: str,
    source_file: str,
    docs_pages: list[str],
) -> dict[str, Any] | None:
    if not name.isupper():
        return None

    value = node.value if isinstance(node, ast.AnnAssign) else node.value
    qualified_name = f"{module}.{name}"
    return {
        "kind": "constant",
        "name": name,
        "qualified_name": qualified_name,
        "fullPath": qualified_name,
        "help": _truncate(_unparse(value), 96),
        "source": _source(source_file=source_file, module=module, object_name=name, line=node.lineno, docs_pages=docs_pages),
    }


def _source(*, source_file: str, module: str, object_name: str, line: int, docs_pages: list[str]) -> dict[str, Any]:
    return {
        "file": source_file,
        "module": module,
        "object": object_name,
        "line": line,
        "docs_pages": docs_pages,
    }


def _insert_module_node(
    *,
    root_node: dict[str, Any],
    package_nodes: dict[str, dict[str, Any]],
    module_node: dict[str, Any],
) -> None:
    module = str(module_node["qualified_name"])
    parts = module.split(".")
    parent = root_node
    prefix = parts[0]

    for part in parts[1:-1]:
        prefix = f"{prefix}.{part}"
        package_node = package_nodes.get(prefix)
        if package_node is None:
            package_node = {
                "kind": "package",
                "name": part,
                "qualified_name": prefix,
                "fullPath": prefix,
                "help": prefix,
                "children": [],
            }
            _children(parent).append(package_node)
            package_nodes[prefix] = package_node
        parent = package_node

    existing_package = package_nodes.get(module)
    if existing_package is not None and existing_package is not module_node:
        existing_package.update({key: value for key, value in module_node.items() if key != "children"})
        _children(existing_package).extend(_children(module_node))
        return

    _children(parent).append(module_node)
    if module_node.get("kind") == "package":
        package_nodes[module] = module_node


def _children(node: dict[str, Any]) -> list[dict[str, Any]]:
    children = node.setdefault("children", [])
    if isinstance(children, list):
        return children
    node["children"] = []
    return node["children"]


def _sort_children(node: dict[str, Any]) -> None:
    children = _children(node)
    children.sort(key=lambda child: (_kind_sort_key(str(child.get("kind"))), str(child.get("name"))))
    for child in children:
        _sort_children(child)


def _kind_sort_key(kind: str) -> int:
    order = {
        "package": 0,
        "module": 1,
        "class": 2,
        "function": 3,
        "async-function": 3,
        "method": 4,
        "constant": 5,
        "export": 6,
    }
    return order.get(kind, 99)


def _module_all(tree: ast.Module) -> set[str] | None:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if not any(isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets):
                continue
            names = _string_sequence(node.value)
            if names is not None:
                return names
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "__all__":
            names = _string_sequence(node.value)
            if names is not None:
                return names
    return None


def _string_sequence(node: ast.AST | None) -> set[str] | None:
    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return None
    names: set[str] = set()
    for element in node.elts:
        if isinstance(element, ast.Constant) and isinstance(element.value, str):
            names.add(element.value)
    return names


def _node_name(node: ast.AST) -> str | None:
    if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
        return node.name
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                return target.id
        return None
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    return None


def _class_signature(node: ast.ClassDef) -> dict[str, str]:
    bases = ", ".join(_unparse(base) for base in node.bases)
    if bases:
        return {"text": f"class {node.name}({bases})"}
    return {"text": f"class {node.name}"}


def _signature_text(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    args = _unparse(node.args)
    returns = f" -> {_unparse(node.returns)}" if node.returns is not None else ""
    return f"{prefix} {node.name}({args}){returns}"


def _summary(doc: str) -> str:
    for line in doc.strip().splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def _unparse(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _truncate(value: str, limit: int) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."
