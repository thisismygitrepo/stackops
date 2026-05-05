import ast
from typing import Any

from stackops.scripts.python.graph.cli_graph_eval import evaluate_typer_config
from stackops.scripts.python.graph.cli_graph_registration import parse_registration
from stackops.scripts.python.graph.cli_graph_resolver import (
    collect_local_imports,
    is_typer_ctor,
    load_module,
)
from stackops.scripts.python.graph.cli_graph_shared import (
    APP_CACHE,
    AppModel,
    AppRef,
    ModuleInfo,
    Registration,
)
from stackops.scripts.python.graph.cli_graph_values import (
    evaluate_condition,
    evaluate_expr,
    value_to_string,
)


def load_app_model(ref: AppRef) -> AppModel:
    cached = APP_CACHE.get(ref)
    if cached is not None:
        return cached

    module_info = load_module(ref.module)
    function_info = module_info.functions.get(ref.factory)
    if function_info is None:
        raise RuntimeError(f"Could not find {ref.module}.{ref.factory}")

    model = extract_app_model(module_info, function_info, ref)
    APP_CACHE[ref] = model
    return model


def extract_app_model(
    module_info: ModuleInfo, function_info: ast.FunctionDef, ref: AppRef
) -> AppModel:
    env: dict[str, Any] = {}
    function_docs = {
        name: ast.get_docstring(func) for name, func in module_info.functions.items()
    }
    app_configs: dict[str, dict[str, Any]] = {}
    registrations: list[Registration] = []
    return_app_var: str | None = None
    order = 0
    local_modules, local_names = collect_local_imports(function_info)

    def process_statements(statements: list[ast.stmt]) -> None:
        nonlocal order
        nonlocal return_app_var

        for statement in statements:
            if isinstance(statement, ast.Assign):
                assign_value = statement.value
                for target in statement.targets:
                    if isinstance(target, ast.Name):
                        if is_typer_ctor(assign_value):
                            app_configs[target.id] = evaluate_typer_config(
                                assign_value, module_info, env, function_docs
                            )
                        else:
                            env[target.id] = evaluate_expr(
                                assign_value, module_info, env, function_docs
                            )
                    elif (
                        isinstance(target, ast.Attribute)
                        and target.attr == "__doc__"
                        and isinstance(target.value, ast.Name)
                    ):
                        function_docs[target.value.id] = value_to_string(
                            evaluate_expr(assign_value, module_info, env, function_docs),
                            fallback=ast.unparse(assign_value),
                        )
                continue

            if isinstance(statement, ast.AnnAssign) and isinstance(
                statement.target, ast.Name
            ):
                ann_value = statement.value
                if ann_value is None:
                    continue
                if is_typer_ctor(ann_value):
                    app_configs[statement.target.id] = evaluate_typer_config(
                        ann_value, module_info, env, function_docs
                    )
                else:
                    env[statement.target.id] = evaluate_expr(
                        ann_value, module_info, env, function_docs
                    )
                continue

            if isinstance(statement, ast.If):
                decision = evaluate_condition(
                    statement.test, module_info, env, function_docs
                )
                if decision is True:
                    process_statements(statement.body)
                elif decision is False:
                    process_statements(statement.orelse)
                else:
                    process_statements(statement.body)
                    process_statements(statement.orelse)
                continue

            if isinstance(statement, ast.Return):
                if isinstance(statement.value, ast.Name):
                    return_app_var = statement.value.id
                continue

            if isinstance(statement, ast.Expr):
                registration = parse_registration(
                    statement.value,
                    module_info=module_info,
                    env=env,
                    function_docs=function_docs,
                    local_modules=local_modules,
                    local_names=local_names,
                    order=order,
                )
                if registration is not None:
                    order += 1
                    registrations.append(registration)
                continue

    process_statements(function_info.body)

    app_var = return_app_var
    if app_var is None and app_configs:
        app_var = next(iter(app_configs))
    if app_var is None:
        raise RuntimeError(
            f"Could not identify Typer app variable in {ref.module}.{ref.factory}"
        )

    app_config = app_configs.get(app_var, {})
    return AppModel(
        ref=ref,
        module_info=module_info,
        app_var=app_var,
        app_config=app_config,
        registrations=registrations,
    )