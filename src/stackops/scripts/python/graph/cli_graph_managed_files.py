import ast

from stackops.scripts.python.graph.cli_graph_eval import evaluate_kwargs
from stackops.scripts.python.graph.cli_graph_registration import parse_registration
from stackops.scripts.python.graph.cli_graph_resolver import collect_local_imports, load_module, resolve_callable
from stackops.scripts.python.graph.cli_graph_shared import ModuleInfo, Registration


def managed_file_registrations(
    expr: ast.AST,
    *,
    module_info: ModuleInfo,
    env: dict[str, object],
    function_docs: dict[str, str | None],
    local_modules: dict[str, str],
    local_names: dict[str, tuple[str, str]],
    order: int,
) -> list[Registration]:
    if not isinstance(expr, ast.Call):
        return []
    resolved = resolve_callable(expr.func, module_info, local_modules=local_modules, local_names=local_names)
    if resolved is None or resolved.module_ref() != "stackops.utils.managed_file_commands.register_managed_file_commands":
        return []
    app_expr = next((keyword.value for keyword in expr.keywords if keyword.arg == "app"), None)
    if not isinstance(app_expr, ast.Name):
        raise ValueError("Managed file command registration requires an app variable.")

    helper_module = load_module(resolved.module)
    helper_function = helper_module.functions[resolved.callable_name]
    helper_env = evaluate_kwargs(expr.keywords, module_info, env, function_docs)
    helper_modules, helper_names = collect_local_imports(helper_function)
    helper_docs: dict[str, str | None] = {}
    for statement in helper_function.body:
        if isinstance(statement, ast.FunctionDef):
            helper_module.functions[statement.name] = statement
            helper_docs[statement.name] = ast.get_docstring(statement)

    registrations: list[Registration] = []
    for statement in helper_function.body:
        if not isinstance(statement, ast.Expr):
            continue
        registration = parse_registration(
            statement.value,
            module_info=helper_module,
            env=helper_env,
            function_docs=helper_docs,
            local_modules=helper_modules,
            local_names=helper_names,
            order=order + len(registrations),
        )
        if registration is None:
            continue
        if not isinstance(registration.target_expr, ast.Name):
            raise ValueError("Managed file command callbacks must be named functions.")
        registration.local_names[registration.target_expr.id] = (resolved.module, registration.target_expr.id)
        registration.app_var = app_expr.id
        registrations.append(registration)
    return registrations
