import ast
from copy import deepcopy
from typing import Any

from stackops.scripts.python.graph.cli_graph_eval import evaluate_typer_config
from stackops.scripts.python.graph.cli_graph_registration import parse_registration
from stackops.scripts.python.graph.cli_graph_resolver import (
    collect_local_imports,
    is_typer_ctor,
    load_module,
    resolve_exported_value,
)
from stackops.scripts.python.graph.cli_graph_shared import (
    APP_CACHE,
    AppModel,
    AppRef,
    ModuleInfo,
    Registration,
    ResolvedModule,
    Unresolved,
)
from stackops.scripts.python.graph.cli_graph_values import (
    evaluate_condition,
    evaluate_expr,
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
    bind_local_imports(
        env=env,
        function_docs=function_docs,
        local_modules=local_modules,
        local_names=local_names,
    )

    def process_registration_expr(expr: ast.AST) -> None:
        nonlocal order

        registration = parse_registration(
            expr,
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

    def process_statements(statements: list[ast.stmt]) -> None:
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
                        doc_value = evaluate_expr(
                            assign_value, module_info, env, function_docs
                        )
                        if isinstance(doc_value, Unresolved):
                            raise RuntimeError(
                                f"Could not resolve {target.value.id}.__doc__ in "
                                f"{module_info.module}: {doc_value.text}"
                            )
                        if not isinstance(doc_value, str):
                            raise RuntimeError(
                                f"Expected {target.value.id}.__doc__ to resolve to str "
                                f"in {module_info.module}, got {type(doc_value).__name__}"
                            )
                        function_docs[target.value.id] = doc_value
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

            if isinstance(statement, ast.For):
                loop_bindings = build_static_loop_bindings(statement)
                if loop_bindings is None:
                    continue
                for binding in loop_bindings:
                    for body_statement in statement.body:
                        bound_statement = replace_bound_names(body_statement, binding)
                        process_statements([bound_statement])
                continue

            if isinstance(statement, ast.Return):
                if isinstance(statement.value, ast.Name):
                    return_app_var = statement.value.id
                continue

            if isinstance(statement, ast.Expr):
                process_registration_expr(statement.value)
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


def bind_local_imports(
    *,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
    local_modules: dict[str, str],
    local_names: dict[str, tuple[str, str]],
) -> None:
    for local_name, module in local_modules.items():
        try:
            load_module(module)
        except FileNotFoundError:
            continue
        env[local_name] = ResolvedModule(module=module)

    for local_name, (module, imported_name) in local_names.items():
        imported_module = f"{module}.{imported_name}"
        try:
            load_module(imported_module)
        except FileNotFoundError:
            pass
        else:
            env[local_name] = ResolvedModule(module=imported_module)
            continue

        try:
            imported_module_info = load_module(module)
        except FileNotFoundError:
            continue

        imported_function = imported_module_info.functions.get(imported_name)
        if imported_function is not None:
            function_docs[local_name] = ast.get_docstring(imported_function)
            continue

        imported_value = resolve_exported_value(module, imported_name)
        if imported_value is not None:
            env[local_name] = imported_value


def build_static_loop_bindings(statement: ast.For) -> list[dict[str, ast.AST]] | None:
    if not isinstance(statement.iter, ast.Tuple | ast.List):
        return None

    bindings: list[dict[str, ast.AST]] = []
    for item in statement.iter.elts:
        binding = bind_loop_target(statement.target, item)
        if binding is None:
            return None
        bindings.append(binding)
    return bindings


def bind_loop_target(target: ast.AST, value: ast.AST) -> dict[str, ast.AST] | None:
    if isinstance(target, ast.Name):
        return {target.id: value}

    if not isinstance(target, ast.Tuple):
        return None
    if not isinstance(value, ast.Tuple | ast.List):
        return None
    if len(target.elts) != len(value.elts):
        return None

    binding: dict[str, ast.AST] = {}
    for target_item, value_item in zip(target.elts, value.elts, strict=True):
        if not isinstance(target_item, ast.Name):
            return None
        binding[target_item.id] = value_item
    return binding


class BoundNameReplacer(ast.NodeTransformer):
    def __init__(self, bindings: dict[str, ast.AST]) -> None:
        self.bindings = bindings

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if not isinstance(node.ctx, ast.Load):
            return node
        replacement = self.bindings.get(node.id)
        if replacement is None:
            return node
        return deepcopy(replacement)


def replace_bound_names(statement: ast.stmt, bindings: dict[str, ast.AST]) -> ast.stmt:
    replaced = BoundNameReplacer(bindings).visit(deepcopy(statement))
    if not isinstance(replaced, ast.stmt):
        raise TypeError(f"Expected statement replacement, got {type(replaced).__name__}")
    return replaced
