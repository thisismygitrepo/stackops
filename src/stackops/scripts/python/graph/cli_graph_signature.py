import ast
from typing import Any

from stackops.scripts.python.graph.cli_graph_resolver import is_name
from stackops.scripts.python.graph.cli_graph_shared import ModuleInfo


def build_signature(
    module_info: ModuleInfo, function_info: ast.FunctionDef
) -> dict[str, Any]:
    parameters = build_parameters(function_info)
    raw_lines = [
        line.rstrip("\n")
        for line in module_info.lines[
            function_info.lineno - 1 : function_info.end_lineno
        ]
    ]
    return_type = (
        ast.unparse(function_info.returns)
        if function_info.returns is not None
        else None
    )

    signature: dict[str, Any] = {
        "raw_lines": raw_lines,
        "name": function_info.name,
        "parameters": parameters,
    }
    if return_type is not None:
        signature["return"] = return_type
    return signature


def build_parameters(function_info: ast.FunctionDef) -> list[dict[str, Any]]:
    parameters: list[dict[str, Any]] = []
    args = function_info.args

    positional = list(args.posonlyargs) + list(args.args)
    positional_defaults = [None] * (len(positional) - len(args.defaults)) + list(
        args.defaults
    )

    for arg, default in zip(positional, positional_defaults, strict=True):
        parameters.append(
            build_parameter(arg=arg, default=default, kind="positional_or_keyword")
        )

    if args.vararg is not None:
        parameters.append(
            build_parameter(arg=args.vararg, default=None, kind="var_positional")
        )

    for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True):
        parameters.append(
            build_parameter(arg=arg, default=default, kind="keyword_only")
        )

    if args.kwarg is not None:
        parameters.append(
            build_parameter(arg=args.kwarg, default=None, kind="var_keyword")
        )

    return parameters


def build_parameter(
    *, arg: ast.arg, default: ast.AST | None, kind: str
) -> dict[str, Any]:
    annotation = arg.annotation
    annotation_raw = ast.unparse(annotation) if annotation is not None else None
    param_type = extract_param_type(annotation)
    typer_info = extract_typer_info(annotation)

    entry: dict[str, Any] = {
        "name": arg.arg,
        "kind": kind,
        "type": param_type,
        "default": serialize_expr(default) if default is not None else None,
        "required": default is None,
    }

    if annotation_raw is not None:
        entry["annotation_raw"] = annotation_raw
    if typer_info is not None:
        entry["typer"] = typer_info
    return entry


def extract_param_type(annotation: ast.AST | None) -> str | None:
    if annotation is None:
        return None
    if isinstance(annotation, ast.Subscript) and is_name(annotation.value, "Annotated"):
        elements = annotation_elements(annotation)
        if elements:
            return ast.unparse(elements[0])
    return ast.unparse(annotation)


def extract_typer_info(annotation: ast.AST | None) -> dict[str, Any] | None:
    if annotation is None:
        return None
    if not (
        isinstance(annotation, ast.Subscript) and is_name(annotation.value, "Annotated")
    ):
        return None

    elements = annotation_elements(annotation)
    for metadata in elements[1:]:
        if not isinstance(metadata, ast.Call):
            continue
        func = metadata.func
        if not (isinstance(func, ast.Attribute) and is_name(func.value, "typer")):
            continue
        if func.attr not in {"Argument", "Option"}:
            continue

        default_value: str | int | float | bool | None = None
        param_decls: list[str] = []
        args = list(metadata.args)
        if args and not isinstance(args[0], ast.Constant | ast.JoinedStr):
            default_value = serialize_expr(args[0])
            args = args[1:]
        elif (
            args
            and isinstance(args[0], ast.Constant)
            and not isinstance(args[0].value, str)
        ):
            default_value = serialize_expr(args[0])
            args = args[1:]

        for value in args:
            string_value = extract_string(value)
            if string_value is not None:
                param_decls.append(string_value)

        long_flags: list[str] = []
        short_flags: list[str] = []
        for decl in param_decls:
            parts = [part.strip() for part in decl.split("/") if part.strip()]
            for part in parts:
                if part.startswith("--"):
                    long_flags.append(part)
                elif part.startswith("-"):
                    short_flags.append(part)

        entry: dict[str, Any] = {
            "kind": "argument" if func.attr == "Argument" else "option",
            "param_decls": param_decls,
            "long_flags": long_flags,
            "short_flags": short_flags,
        }
        help_value = keyword_value(metadata, "help")
        if isinstance(help_value, str):
            entry["help"] = help_value
        if default_value is not None:
            entry["default"] = default_value
        return entry
    return None


def annotation_elements(annotation: ast.Subscript) -> list[ast.AST]:
    slice_value = annotation.slice
    if isinstance(slice_value, ast.Tuple):
        return list(slice_value.elts)
    return [slice_value]


def keyword_value(call: ast.Call, name: str) -> str | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return extract_string(keyword.value)
    return None


def extract_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    return None


def serialize_expr(node: ast.AST | None) -> Any:
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        if node.value is Ellipsis:
            return "..."
        return node.value
    if isinstance(node, ast.List):
        return [serialize_expr(elt) for elt in node.elts]
    if isinstance(node, ast.Tuple):
        return [serialize_expr(elt) for elt in node.elts]
    if isinstance(node, ast.Dict):
        result: dict[str, Any] = {}
        for key, value in zip(node.keys, node.values, strict=True):
            key_value = serialize_expr(key)
            if isinstance(key_value, str):
                result[key_value] = serialize_expr(value)
        return result
    return ast.unparse(node)