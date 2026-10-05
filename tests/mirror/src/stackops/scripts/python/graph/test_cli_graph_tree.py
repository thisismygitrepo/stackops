import ast
from typing import NotRequired, TypedDict, cast

from stackops.scripts.python.graph.cli_graph_shared import REPO_ROOT, SRC_ROOT
from stackops.scripts.python.graph.cli_graph_tree import build_cli_graph


class GraphTyperInfo(TypedDict):
    kind: str
    param_decls: list[str]
    short_flags: list[str]


class GraphParameter(TypedDict):
    name: str
    typer: NotRequired[GraphTyperInfo]


class GraphSignature(TypedDict):
    parameters: list[GraphParameter]


class GraphSource(TypedDict):
    file: str


class GraphNode(TypedDict):
    fullPath: str
    source: GraphSource
    children: NotRequired[list["GraphNode"]]
    signature: NotRequired[GraphSignature]


class CliGraphPayload(TypedDict):
    root: GraphNode


def test_every_registered_typer_option_has_a_single_letter_short_alias() -> None:
    graph = cast(CliGraphPayload, build_cli_graph())
    pending_nodes = [graph["root"]]
    missing_aliases: list[str] = []

    while pending_nodes:
        node = pending_nodes.pop()
        pending_nodes.extend(node.get("children", []))
        signature = node.get("signature")
        if signature is None:
            continue

        for parameter in signature["parameters"]:
            typer_info = parameter.get("typer")
            if typer_info is None or typer_info["kind"] != "option":
                continue
            if any(len(flag) == 2 and flag.startswith("-") and not flag.startswith("--") for flag in typer_info["short_flags"]):
                continue
            missing_aliases.append(f"{node['source']['file']}:{node['fullPath']} {parameter['name']} {typer_info['param_decls']}")

    assert sorted(missing_aliases) == []


def test_every_typer_option_declaration_has_a_single_letter_short_alias() -> None:
    missing_aliases: list[str] = []

    for path in sorted(SRC_ROOT.rglob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(module):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if not isinstance(node.func.value, ast.Name) or node.func.value.id != "typer" or node.func.attr != "Option":
                continue

            declarations = [argument.value for argument in node.args if isinstance(argument, ast.Constant) and isinstance(argument.value, str)]
            if any(len(part) == 2 and part.startswith("-") and part[1].isalpha() for part in declarations):
                continue
            missing_aliases.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} {declarations}")

    assert sorted(missing_aliases) == []


def test_typer_boolean_options_use_single_flags_with_false_defaults() -> None:
    violations: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"))
        for function in ast.walk(module):
            if not isinstance(function, ast.FunctionDef):
                continue
            arguments = function.args.posonlyargs + function.args.args
            defaults = [None] * (len(arguments) - len(function.args.defaults)) + list(function.args.defaults)
            for argument, default in zip(arguments, defaults, strict=True):
                if argument.annotation is None:
                    continue
                for node in ast.walk(argument.annotation):
                    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                        continue
                    if not isinstance(node.func.value, ast.Name) or node.func.value.id != "typer" or node.func.attr != "Option":
                        continue
                    declarations = [item.value for item in node.args if isinstance(item, ast.Constant) and isinstance(item.value, str)]
                    if any("/" in declaration for declaration in declarations):
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} paired flags {declarations}")
                    if isinstance(default, ast.Constant) and default.value is True:
                        violations.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno} inert default-on flag {declarations}")
    assert violations == []
