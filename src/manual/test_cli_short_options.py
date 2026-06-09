from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "src" / "stackops"


def test_typer_options_have_single_letter_short_aliases_only() -> None:
    failures: list[str] = []

    for path in sorted(SOURCE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        visitor = _TyperOptionVisitor(path=path.relative_to(REPO_ROOT))
        visitor.visit(tree)
        failures.extend(visitor.failures)

    assert failures == []


def test_checked_in_cli_hierarchy_short_names_are_single_letter() -> None:
    failures: list[str] = []
    for path in [
        SOURCE_ROOT / "utils" / "cli_utils" / "hierarchy.py",
        SOURCE_ROOT / "utils" / "cli_utils" / "hierarchy_types.py",
    ]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values, strict=False):
                if _string_literal_value(key) != "short_name":
                    continue
                short_name = _literal_string_value(value)
                if short_name is not None and len(short_name) != 1:
                    failures.append(f"{path.relative_to(REPO_ROOT)}:{value.lineno} short_name is not one letter: {short_name!r}")

    assert failures == []


class _TyperOptionVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.function_stack: list[str] = []
        self.option_declarations_by_function: dict[str, list[_OptionDeclaration]] = defaultdict(list)
        self.failures: list[str] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.function_stack.append(node.name)
        self.generic_visit(node)
        function_name = ".".join(self.function_stack)
        self._record_duplicate_short_aliases(function_name=function_name)
        self.function_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        self._check_hidden_command_alias(node)
        if _is_typer_option_call(node):
            option_strings = [value for arg in node.args if (value := _string_literal_value(arg)) is not None]
            short_aliases = [part for option in option_strings for part in _short_option_parts(option)]
            one_letter_aliases = [alias for alias in short_aliases if len(alias) == 2]
            multi_letter_aliases = [alias for alias in short_aliases if len(alias) > 2]
            function_name = ".".join(self.function_stack) or "<module>"
            declaration = _OptionDeclaration(lineno=node.lineno, function_name=function_name, option_strings=option_strings, short_aliases=one_letter_aliases)
            self.option_declarations_by_function[function_name].append(declaration)

            if not one_letter_aliases:
                self.failures.append(f"{self.path}:{node.lineno} {function_name} has no one-letter short alias: {option_strings}")
            if multi_letter_aliases:
                self.failures.append(f"{self.path}:{node.lineno} {function_name} has multi-letter short alias: {multi_letter_aliases}")

        self.generic_visit(node)

    def _check_hidden_command_alias(self, node: ast.Call) -> None:
        if not _is_typer_command_or_group_call(node):
            return
        if not _is_hidden_call(node):
            return
        command_name = _command_or_group_name(node)
        if command_name is not None and len(command_name) != 1:
            function_name = ".".join(self.function_stack) or "<module>"
            self.failures.append(f"{self.path}:{node.lineno} {function_name} hidden command alias is not one letter: {command_name!r}")

    def _record_duplicate_short_aliases(self, function_name: str) -> None:
        declarations = self.option_declarations_by_function.get(function_name, [])
        aliases_to_declarations: dict[str, list[_OptionDeclaration]] = defaultdict(list)
        for declaration in declarations:
            for alias in declaration.short_aliases:
                aliases_to_declarations[alias].append(declaration)

        for alias, alias_declarations in aliases_to_declarations.items():
            if len(alias_declarations) < 2:
                continue
            locations = ", ".join(f"line {declaration.lineno}: {declaration.option_strings}" for declaration in alias_declarations)
            self.failures.append(f"{self.path} {function_name} duplicates {alias}: {locations}")


class _OptionDeclaration:
    def __init__(self, *, lineno: int, function_name: str, option_strings: list[str], short_aliases: list[str]) -> None:
        self.lineno = lineno
        self.function_name = function_name
        self.option_strings = option_strings
        self.short_aliases = short_aliases


def _is_typer_option_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "Option"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "typer"
    )


def _is_typer_command_or_group_call(node: ast.AST) -> bool:
    return isinstance(node.func, ast.Attribute) and node.func.attr in {"command", "add_typer"}


def _is_hidden_call(node: ast.Call) -> bool:
    for keyword in node.keywords:
        if keyword.arg == "hidden" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is True
    return False


def _command_or_group_name(node: ast.Call) -> str | None:
    if node.args and (value := _string_literal_value(node.args[0])) is not None:
        return value
    for keyword in node.keywords:
        if keyword.arg == "name":
            return _string_literal_value(keyword.value)
    return None


def _string_literal_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_string_value(node: ast.AST) -> str | None:
    value = _string_literal_value(node)
    if value is not None:
        return value
    if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == "Literal":
        return _string_literal_value(node.slice)
    return None


def _short_option_parts(option_string: str) -> list[str]:
    if not option_string.startswith("-") or option_string.startswith("--"):
        return []
    return [part for part in option_string.split("/") if part.startswith("-") and not part.startswith("--")]
