import ast
from pathlib import Path
from typing import Any

from stackops.scripts.python.graph.cli_graph_resolver import (
    is_name,
    literal_values,
    resolve_imported_symbol,
)
from stackops.scripts.python.graph.cli_graph_shared import ModuleInfo, Unresolved


def evaluate_condition(
    expr: ast.AST,
    module_info: ModuleInfo,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
) -> bool | None:
    value = evaluate_expr(expr, module_info, env, function_docs)
    if isinstance(value, Unresolved):
        return None
    if isinstance(value, bool):
        return value
    return None


def evaluate_expr(
    expr: ast.AST,
    module_info: ModuleInfo,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
) -> Any:
    if isinstance(expr, ast.Constant):
        return expr.value

    if isinstance(expr, ast.Name):
        if expr.id in env:
            return env[expr.id]
        if expr.id in function_docs:
            return {"__doc__": function_docs[expr.id] or ""}
        imported = resolve_imported_symbol(module_info, expr.id)
        if imported is not None:
            return imported
        return Unresolved(expr.id)

    if isinstance(expr, ast.JoinedStr):
        parts: list[str] = []
        for value in expr.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
                continue
            if isinstance(value, ast.FormattedValue):
                formatted = evaluate_expr(value.value, module_info, env, function_docs)
                if isinstance(formatted, Unresolved):
                    return Unresolved(ast.unparse(expr))
                parts.append(str(formatted))
                continue
            return Unresolved(ast.unparse(expr))
        return "".join(parts)

    if isinstance(expr, ast.List):
        return [
            simplify_value(
                evaluate_expr(item, module_info, env, function_docs),
                fallback=ast.unparse(item),
            )
            for item in expr.elts
        ]

    if isinstance(expr, ast.Tuple):
        return tuple(
            simplify_value(
                evaluate_expr(item, module_info, env, function_docs),
                fallback=ast.unparse(item),
            )
            for item in expr.elts
        )

    if isinstance(expr, ast.Dict):
        result: dict[str, Any] = {}
        for key, value in zip(expr.keys, expr.values, strict=True):
            if key is None:
                return Unresolved(ast.unparse(expr))
            key_value = evaluate_expr(key, module_info, env, function_docs)
            if isinstance(key_value, Unresolved) or not isinstance(key_value, str):
                return Unresolved(ast.unparse(expr))
            result[key_value] = simplify_value(
                evaluate_expr(value, module_info, env, function_docs),
                fallback=ast.unparse(value),
            )
        return result

    if isinstance(expr, ast.Attribute):
        base = evaluate_expr(expr.value, module_info, env, function_docs)
        if expr.attr == "__doc__" and isinstance(base, dict):
            return base.get("__doc__", "")
        return Unresolved(ast.unparse(expr))

    if isinstance(expr, ast.Subscript):
        base = evaluate_expr(expr.value, module_info, env, function_docs)
        key = evaluate_expr(expr.slice, module_info, env, function_docs)
        if isinstance(base, Unresolved) or isinstance(key, Unresolved):
            return Unresolved(ast.unparse(expr))
        try:
            return base[key]
        except Exception:
            return Unresolved(ast.unparse(expr))

    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        value = evaluate_expr(expr.operand, module_info, env, function_docs)
        if isinstance(value, Unresolved):
            return value
        return not bool(value)

    if isinstance(expr, ast.BoolOp):
        values = [
            evaluate_expr(value, module_info, env, function_docs)
            for value in expr.values
        ]
        if any(isinstance(value, Unresolved) for value in values):
            return Unresolved(ast.unparse(expr))
        if isinstance(expr.op, ast.And):
            return all(bool(value) for value in values)
        if isinstance(expr.op, ast.Or):
            return any(bool(value) for value in values)

    if (
        isinstance(expr, ast.Compare)
        and len(expr.ops) == 1
        and len(expr.comparators) == 1
    ):
        left = evaluate_expr(expr.left, module_info, env, function_docs)
        right = evaluate_expr(expr.comparators[0], module_info, env, function_docs)
        if isinstance(left, Unresolved) or isinstance(right, Unresolved):
            return Unresolved(ast.unparse(expr))
        op = expr.ops[0]
        if isinstance(op, ast.Eq):
            return left == right
        if isinstance(op, ast.NotEq):
            return left != right

    if isinstance(expr, ast.Call):
        return evaluate_call(expr, module_info, env, function_docs)

    if isinstance(expr, ast.Subscript) and is_name(expr.value, "Literal"):
        values = literal_values(expr)
        return tuple(values)

    return Unresolved(ast.unparse(expr))


def evaluate_call(
    expr: ast.Call,
    module_info: ModuleInfo,
    env: dict[str, Any],
    function_docs: dict[str, str | None],
) -> Any:
    if is_name(expr.func, "get_args") and len(expr.args) == 1:
        value = evaluate_expr(expr.args[0], module_info, env, function_docs)
        if isinstance(value, Unresolved):
            return value
        if isinstance(value, tuple):
            return value
        if isinstance(value, list):
            return tuple(value)
        return Unresolved(ast.unparse(expr))

    if (
        isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "join"
        and len(expr.args) == 1
    ):
        base = evaluate_expr(expr.func.value, module_info, env, function_docs)
        value = evaluate_expr(expr.args[0], module_info, env, function_docs)
        if isinstance(base, str) and not isinstance(value, Unresolved):
            if isinstance(value, tuple):
                return base.join(str(item) for item in value)
            if isinstance(value, list):
                return base.join(str(item) for item in value)
        return Unresolved(ast.unparse(expr))

    if (
        isinstance(expr.func, ast.Attribute)
        and expr.func.attr == "home"
        and is_name(expr.func.value, "Path")
    ):
        if expr.args or expr.keywords:
            return Unresolved(ast.unparse(expr))
        return Path.home()

    if isinstance(expr.func, ast.Attribute) and expr.func.attr == "joinpath":
        base = evaluate_expr(expr.func.value, module_info, env, function_docs)
        if isinstance(base, Path):
            args: list[str] = []
            for arg in expr.args:
                value = evaluate_expr(arg, module_info, env, function_docs)
                if isinstance(value, Unresolved):
                    return value
                args.append(str(value))
            return base.joinpath(*args)
        return Unresolved(ast.unparse(expr))

    if isinstance(expr.func, ast.Attribute) and expr.func.attr == "exists":
        base = evaluate_expr(expr.func.value, module_info, env, function_docs)
        if isinstance(base, Path) and not expr.args and not expr.keywords:
            return base.exists()
        return Unresolved(ast.unparse(expr))

    return Unresolved(ast.unparse(expr))


def simplify_value(value: Any, *, fallback: str) -> Any:
    if isinstance(value, Unresolved):
        return value.text
    if isinstance(value, tuple):
        return [simplify_value(item, fallback=str(item)) for item in value]
    if isinstance(value, list):
        return [simplify_value(item, fallback=str(item)) for item in value]
    if isinstance(value, dict):
        simplified: dict[str, Any] = {}
        for key, item in value.items():
            simplified[str(key)] = simplify_value(item, fallback=str(item))
        return simplified
    return value if value is not None else fallback if fallback == "None" else value


def value_to_string(value: Any, *, fallback: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Unresolved):
        return value.text
    return fallback