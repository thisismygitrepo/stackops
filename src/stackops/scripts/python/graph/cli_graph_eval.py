import ast
from typing import Any

from stackops.scripts.python.graph.cli_graph_shared import ModuleInfo, Unresolved
from stackops.scripts.python.graph.cli_graph_values import evaluate_expr, simplify_value


def evaluate_typer_config(
    call: ast.AST,
    module_info: ModuleInfo,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
) -> dict[str, Any]:
    if not isinstance(call, ast.Call):
        return {}
    return evaluate_kwargs(call.keywords, module_info, env, function_docs)


def evaluate_kwargs(
    keywords: list[ast.keyword],
    module_info: ModuleInfo,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for keyword in keywords:
        if keyword.arg is None:
            continue
        value = evaluate_expr(keyword.value, module_info, env, function_docs)
        if keyword.arg in {"help", "short_help"}:
            if isinstance(value, Unresolved):
                raise RuntimeError(
                    f"Could not resolve {keyword.arg} in {module_info.module}: "
                    f"{value.text}"
                )
            if value is not None and not isinstance(value, str):
                raise RuntimeError(
                    f"Expected {keyword.arg} to resolve to str or None in "
                    f"{module_info.module}, got {type(value).__name__}"
                )
            result[keyword.arg] = value
            continue
        result[keyword.arg] = simplify_value(
            value,
            fallback=ast.unparse(keyword.value),
        )
    return result
