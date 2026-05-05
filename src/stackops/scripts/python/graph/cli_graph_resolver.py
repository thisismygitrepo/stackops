import ast
from pathlib import Path
from typing import Any

from stackops.scripts.python.graph.cli_graph_shared import (
    EXPORT_CACHE,
    MODULE_CACHE,
    ModuleInfo,
    ResolvedCallable,
    SRC_ROOT,
)


def resolve_imported_symbol(module_info: ModuleInfo, name: str) -> Any | None:
    if name in module_info.imported_names:
        module, attr = module_info.imported_names[name]
        if module == "pathlib" and attr == "Path":
            return Path
        if module == "typing" and attr == "get_args":
            return "get_args"
        return resolve_exported_value(module, attr)
    return None


def resolve_exported_value(module: str, attr: str) -> Any | None:
    cache_key = (module, attr)
    if cache_key in EXPORT_CACHE:
        return EXPORT_CACHE[cache_key]

    try:
        module_info = load_module(module)
    except FileNotFoundError:
        EXPORT_CACHE[cache_key] = None
        return None

    if attr in module_info.assignments:
        value = evaluate_module_assignment(module_info.assignments[attr])
        EXPORT_CACHE[cache_key] = value
        return value

    if attr in module_info.imported_names:
        imported_module, imported_attr = module_info.imported_names[attr]
        value = resolve_exported_value(imported_module, imported_attr)
        EXPORT_CACHE[cache_key] = value
        return value

    EXPORT_CACHE[cache_key] = None
    return None


def evaluate_module_assignment(expr: ast.AST) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value
    if isinstance(expr, ast.Subscript) and is_name(expr.value, "Literal"):
        return tuple(literal_values(expr))
    return None


def literal_values(expr: ast.Subscript) -> list[Any]:
    slice_value = expr.slice
    values = (
        list(slice_value.elts) if isinstance(slice_value, ast.Tuple) else [slice_value]
    )
    result: list[Any] = []
    for value in values:
        if isinstance(value, ast.Constant):
            result.append(value.value)
        else:
            result.append(ast.unparse(value))
    return result


def load_module(module: str) -> ModuleInfo:
    cached = MODULE_CACHE.get(module)
    if cached is not None:
        return cached

    path = module_to_path(module)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)
    info = ModuleInfo(module=module, path=path, tree=tree, source=source, lines=lines)

    for statement in tree.body:
        if isinstance(statement, ast.FunctionDef):
            info.functions[statement.name] = statement
        elif isinstance(statement, ast.Import):
            for alias in statement.names:
                local = alias.asname or alias.name
                info.imported_modules[local] = alias.name
        elif isinstance(statement, ast.ImportFrom) and statement.module is not None:
            for alias in statement.names:
                local = alias.asname or alias.name
                info.imported_names[local] = (statement.module, alias.name)
        elif isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name):
                    info.assignments[target.id] = statement.value
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.value is not None
        ):
            info.assignments[statement.target.id] = statement.value

    MODULE_CACHE[module] = info
    return info


def module_to_path(module: str) -> Path:
    parts = module.split(".")
    direct = SRC_ROOT.joinpath(*parts).with_suffix(".py")
    if direct.exists():
        return direct
    package = SRC_ROOT.joinpath(*parts, "__init__.py")
    if package.exists():
        return package
    raise FileNotFoundError(f"Could not resolve module path for {module}")


def resolve_callable(
    expr: ast.AST,
    module_info: ModuleInfo,
    *,
    local_modules: dict[str, str] | None = None,
    local_names: dict[str, tuple[str, str]] | None = None,
) -> ResolvedCallable | None:
    dotted = dotted_name(expr)
    if dotted is None:
        return None

    parts = dotted.split(".")
    root = parts[0]
    imported_modules = dict(module_info.imported_modules)
    imported_names = dict(module_info.imported_names)
    if local_modules:
        imported_modules.update(local_modules)
    if local_names:
        imported_names.update(local_names)

    if root in module_info.functions and len(parts) == 1:
        return ResolvedCallable(module=module_info.module, callable_name=root)

    if root in imported_names:
        imported_module, imported_attr = imported_names[root]
        full = ".".join([imported_module, imported_attr, *parts[1:]])
        split = split_module_and_callable(full)
        if split is not None:
            return ResolvedCallable(module=split[0], callable_name=split[1])

    if root in imported_modules:
        full = ".".join([imported_modules[root], *parts[1:]])
        split = split_module_and_callable(full)
        if split is not None:
            return ResolvedCallable(module=split[0], callable_name=split[1])

    if root == "stackops":
        split = split_module_and_callable(dotted)
        if split is not None:
            return ResolvedCallable(module=split[0], callable_name=split[1])

    return None


def split_module_and_callable(reference: str) -> tuple[str, str] | None:
    parts = reference.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module = ".".join(parts[:index])
        callable_name = parts[index]
        try:
            module_to_path(module)
        except FileNotFoundError:
            continue
        return module, callable_name
    return None


def dotted_name(expr: ast.AST) -> str | None:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        parent = dotted_name(expr.value)
        if parent is None:
            return None
        return f"{parent}.{expr.attr}"
    return None


def collect_local_imports(
    function_info: ast.FunctionDef,
) -> tuple[dict[str, str], dict[str, tuple[str, str]]]:
    imported_modules: dict[str, str] = {}
    imported_names: dict[str, tuple[str, str]] = {}

    for node in ast.walk(function_info):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                imported_modules[local] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            for alias in node.names:
                local = alias.asname or alias.name
                imported_names[local] = (node.module, alias.name)

    return imported_modules, imported_names


def is_typer_ctor(expr: ast.AST) -> bool:
    return (
        isinstance(expr, ast.Call)
        and isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "Typer"
        and is_name(expr.func.value, "typer")
    )


def is_name(expr: ast.AST, name: str) -> bool:
    return isinstance(expr, ast.Name) and expr.id == name