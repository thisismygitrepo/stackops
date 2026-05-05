import ast

from stackops.scripts.python.graph.cli_graph_resolver import (
    collect_local_imports,
    load_module,
    resolve_callable,
)
from stackops.scripts.python.graph.cli_graph_shared import (
    AppRef,
    ModuleInfo,
    Registration,
    ResolvedCallable,
)


def registration_key(reg: Registration, module_info: ModuleInfo) -> tuple[str, str]:
    if reg.kind == "add_typer":
        child_ref = resolve_registration_child_app_ref(reg, module_info)
        if child_ref is None:
            name = reg.name or ast.unparse(reg.target_expr)
            return ("group", f"{module_info.module}:{name}")
        return ("group", f"{child_ref.module}.{child_ref.factory}")

    resolved = resolve_registration_callable(reg, module_info)
    if resolved is None:
        name = reg.name or ast.unparse(reg.target_expr)
        return ("command", f"{module_info.module}:{name}")

    dispatch_ref = find_dispatch_target(resolved)
    if dispatch_ref is not None:
        return ("group", f"{dispatch_ref.module}.{dispatch_ref.factory}")
    return ("command", resolved.module_ref())


def resolve_group_target(reg: Registration, module_info: ModuleInfo) -> AppRef | None:
    if reg.kind == "add_typer":
        return resolve_registration_child_app_ref(reg, module_info)

    resolved = resolve_registration_callable(reg, module_info)
    if resolved is None:
        return None
    return find_dispatch_target(resolved)


def resolve_registration_callable(
    reg: Registration, module_info: ModuleInfo
) -> ResolvedCallable | None:
    return resolve_callable(
        reg.target_expr,
        module_info,
        local_modules=reg.local_modules,
        local_names=reg.local_names,
    )


def resolve_registration_child_app_ref(
    reg: Registration, module_info: ModuleInfo
) -> AppRef | None:
    return resolve_child_app_ref(
        reg.target_expr,
        module_info,
        local_modules=reg.local_modules,
        local_names=reg.local_names,
    )


def find_dispatch_target(resolved: ResolvedCallable) -> AppRef | None:
    module_info = load_module(resolved.module)
    function_info = module_info.functions.get(resolved.callable_name)
    if function_info is None:
        return None

    local_modules, local_names = collect_local_imports(function_info)
    for node in ast.walk(function_info):
        if not isinstance(node, ast.Call):
            continue
        inner = node.func
        if not isinstance(inner, ast.Call):
            continue
        child_ref = resolve_child_app_ref(
            inner, module_info, local_modules=local_modules, local_names=local_names
        )
        if child_ref is not None:
            return child_ref
    return None


def resolve_child_app_ref(
    expr: ast.AST,
    module_info: ModuleInfo,
    *,
    local_modules: dict[str, str] | None = None,
    local_names: dict[str, tuple[str, str]] | None = None,
) -> AppRef | None:
    if not isinstance(expr, ast.Call):
        return None

    resolved = resolve_callable(
        expr.func, module_info, local_modules=local_modules, local_names=local_names
    )
    if resolved is None or resolved.callable_name != "get_app":
        return None
    return AppRef(module=resolved.module, factory=resolved.callable_name)