import ast
from typing import Any, Sequence

from stackops.scripts.python.graph.cli_graph_eval import evaluate_kwargs
from stackops.scripts.python.graph.cli_graph_shared import ModuleInfo, Registration


def parse_registration(
    expr: ast.AST,
    *,
    module_info: ModuleInfo,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
    local_modules: dict[str, str],
    local_names: dict[str, tuple[str, str]],
    order: int,
) -> Registration | None:
    if not isinstance(expr, ast.Call):
        return None

    if isinstance(expr.func, ast.Call):
        inner = expr.func
        if not isinstance(inner.func, ast.Attribute) or inner.func.attr != "command":
            return None
        if not isinstance(inner.func.value, ast.Name):
            return None
        if len(expr.args) != 1:
            return None

        app_var = inner.func.value.id
        kwargs = evaluate_kwargs(inner.keywords, module_info, env, function_docs)
        name = registration_name(inner.args, kwargs)
        typer_config = registration_typer_config(kwargs)
        return Registration(
            kind="command",
            app_var=app_var,
            target_expr=expr.args[0],
            order=order,
            local_modules=local_modules,
            local_names=local_names,
            name=name,
            hidden=bool(kwargs.get("hidden", False)),
            help=kwargs.get("help"),
            short_help=kwargs.get("short_help"),
            context_settings=kwargs.get("context_settings"),
            typer_config=typer_config,
        )

    if not isinstance(expr.func, ast.Attribute) or expr.func.attr != "add_typer":
        return None
    if not isinstance(expr.func.value, ast.Name):
        return None
    if not expr.args:
        return None

    app_var = expr.func.value.id
    kwargs = evaluate_kwargs(expr.keywords, module_info, env, function_docs)
    name = registration_name([], kwargs)
    return Registration(
        kind="add_typer",
        app_var=app_var,
        target_expr=expr.args[0],
        order=order,
        local_modules=local_modules,
        local_names=local_names,
        name=name,
        hidden=bool(kwargs.get("hidden", False)),
        help=kwargs.get("help"),
        short_help=kwargs.get("short_help"),
        context_settings=kwargs.get("context_settings"),
        typer_config=registration_typer_config(kwargs),
    )


def registration_name(args: Sequence[ast.AST], kwargs: dict[str, Any]) -> str | None:
    if "name" in kwargs and isinstance(kwargs["name"], str):
        return kwargs["name"]
    if args:
        first = args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    return None


def registration_typer_config(kwargs: dict[str, Any]) -> dict[str, Any]:
    excluded = {"name", "help", "short_help", "hidden", "context_settings"}
    return {key: value for key, value in kwargs.items() if key not in excluded}