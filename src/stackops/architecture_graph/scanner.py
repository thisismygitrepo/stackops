import ast
from dataclasses import dataclass
from pathlib import Path

from stackops.architecture_graph.models import InternalImport, ModuleName, PythonModule


@dataclass(frozen=True, slots=True)
class ImportCandidate:
    name: ModuleName
    line: int


def discover_python_modules(source_root: Path, package_name: str) -> list[PythonModule]:
    return [
        PythonModule(name=module_name_from_path(path, source_root, package_name), path=path)
        for path in sorted(source_root.rglob("*.py"))
        if "__pycache__" not in path.parts
    ]


def collect_internal_imports(modules: list[PythonModule], package_name: str) -> list[InternalImport]:
    known_modules = frozenset(module.name for module in modules)
    imports: list[InternalImport] = []
    for module in modules:
        source = module.path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module.path))
        current_package = current_package_name(module)
        for candidate in collect_import_candidates(tree, current_package):
            imported = resolve_known_internal_module(candidate.name, known_modules, package_name)
            if imported is not None and imported != module.name:
                imports.append(
                    InternalImport(
                        importer=module.name,
                        imported=imported,
                        path=module.path,
                        line=candidate.line,
                    )
                )
    return imports


def module_name_from_path(path: Path, source_root: Path, package_name: str) -> ModuleName:
    relative = path.relative_to(source_root)
    parts = [package_name, *relative.with_suffix("").parts]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def current_package_name(module: PythonModule) -> ModuleName:
    if module.path.name == "__init__.py":
        return module.name
    return module.name.rpartition(".")[0]


def collect_import_candidates(tree: ast.AST, current_package: ModuleName) -> list[ImportCandidate]:
    candidates: list[ImportCandidate] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            candidates.extend(ImportCandidate(name=alias.name, line=node.lineno) for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            candidates.extend(import_from_candidates(node, current_package))
    return candidates


def import_from_candidates(node: ast.ImportFrom, current_package: ModuleName) -> list[ImportCandidate]:
    base_module = absolute_import_from_base(node, current_package)
    if base_module is None:
        return []
    candidates: list[ImportCandidate] = []
    for alias in node.names:
        if alias.name == "*":
            candidates.append(ImportCandidate(name=base_module, line=node.lineno))
        else:
            candidates.append(ImportCandidate(name=f"{base_module}.{alias.name}", line=node.lineno))
    return candidates


def absolute_import_from_base(node: ast.ImportFrom, current_package: ModuleName) -> ModuleName | None:
    if node.level == 0:
        return node.module
    package_parts = current_package.split(".")
    remove_count = node.level - 1
    if remove_count >= len(package_parts):
        return None
    base_parts = package_parts[: len(package_parts) - remove_count]
    if node.module is not None:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def resolve_known_internal_module(
    candidate: ModuleName,
    known_modules: frozenset[ModuleName],
    package_name: str,
) -> ModuleName | None:
    if candidate != package_name and not candidate.startswith(f"{package_name}."):
        return None
    parts = candidate.split(".")
    while len(parts) > 0:
        module_name = ".".join(parts)
        if module_name in known_modules:
            return module_name
        parts = parts[:-1]
    return None
