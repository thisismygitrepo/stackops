from __future__ import annotations

import ast
import os
import posixpath
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT.joinpath("src", "machineconfig")
BODY_FIELD_NAMES = frozenset({"body", "orelse", "finalbody"})
FD_COMMAND = ("fd", "-t", "f", "-E", ".venv", "-E", "docs", "-E", "tests", "-E", "*.py")
PATH_REFERENCE_HELPERS = frozenset({"get_path_reference_path", "get_path_reference_library_relative_path"})


@dataclass(frozen=True, slots=True)
class AssetDefinition:
    relative_path: str
    basename: str
    init_file: Path
    variable_name: str


@dataclass(frozen=True, slots=True)
class PathExprState:
    anchored: bool
    literal_path: str | None
    uses_path_reference: bool


@dataclass(frozen=True, slots=True)
class PathReferenceViolation:
    python_file: Path
    line_number: int
    asset: AssetDefinition
    expression: str


def _list_asset_relative_paths() -> tuple[str, ...]:
    result = subprocess.run(
        FD_COMMAND,
        cwd=SRC_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return tuple(line for line in result.stdout.splitlines() if line != "")


def _literal_string(node: ast.expr) -> str | None:
    try:
        value = ast.literal_eval(node)
    except (SyntaxError, ValueError):
        return None
    if isinstance(value, str):
        return value
    return None


def _extract_init_path_references(init_file: Path) -> dict[str, str]:
    tree = ast.parse(init_file.read_text(encoding="utf-8"), filename=init_file.as_posix())
    references: dict[str, str] = {}
    for statement in tree.body:
        target_name: str | None = None
        value_node: ast.expr | None = None
        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1 or not isinstance(statement.targets[0], ast.Name):
                continue
            target_name = statement.targets[0].id
            value_node = statement.value
        elif isinstance(statement, ast.AnnAssign):
            if not isinstance(statement.target, ast.Name):
                continue
            target_name = statement.target.id
            value_node = statement.value
        if target_name is None or value_node is None or "_PATH_REFERENCE" not in target_name:
            continue
        literal = _literal_string(value_node)
        if literal is None:
            continue
        references[literal] = target_name
    return references


def _collect_assets() -> tuple[tuple[AssetDefinition, ...], tuple[str, ...]]:
    assets: list[AssetDefinition] = []
    failures: list[str] = []
    for relative_path in _list_asset_relative_paths():
        asset_path = SRC_ROOT.joinpath(relative_path)
        init_file = asset_path.parent.joinpath("__init__.py")
        if not init_file.is_file():
            failures.append(f"{relative_path}: missing sibling __init__.py")
            continue
        references = _extract_init_path_references(init_file=init_file)
        variable_name = references.get(asset_path.name)
        if variable_name is None:
            failures.append(f"{relative_path}: missing sibling _PATH_REFERENCE for {asset_path.name}")
            continue
        assets.append(
            AssetDefinition(
                relative_path=relative_path,
                basename=asset_path.name,
                init_file=init_file,
                variable_name=variable_name,
            )
        )
    return tuple(sorted(assets, key=lambda asset: asset.relative_path)), tuple(failures)


def _build_unique_basename_map(assets: tuple[AssetDefinition, ...]) -> dict[str, AssetDefinition]:
    grouped: dict[str, list[AssetDefinition]] = {}
    for asset in assets:
        grouped.setdefault(asset.basename, []).append(asset)
    return {basename: grouped_assets[0] for basename, grouped_assets in grouped.items() if len(grouped_assets) == 1}


def _normalize_path(value: str) -> str:
    return value.replace("\\", "/")


def _join_literal_paths(left: str | None, right: str | None) -> str | None:
    if left is None and right is None:
        return None
    if left is None:
        return right
    if right is None:
        return left
    return posixpath.join(left, right)


def _parent_literal_path(literal_path: str | None) -> str | None:
    if literal_path is None or "/" not in literal_path:
        return None
    return posixpath.dirname(literal_path)


def _get_call_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _infer_path_expr_state(expression: ast.expr | None, scope: dict[str, PathExprState]) -> PathExprState | None:
    if expression is None:
        return None
    if isinstance(expression, ast.Name):
        if expression.id in scope:
            return scope[expression.id]
        if expression.id.endswith("_PATH_REFERENCE"):
            return PathExprState(anchored=False, literal_path=None, uses_path_reference=True)
        return None
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        return PathExprState(anchored=False, literal_path=_normalize_path(expression.value), uses_path_reference=False)
    if isinstance(expression, ast.Attribute):
        if expression.attr == "__file__":
            return PathExprState(anchored=True, literal_path=None, uses_path_reference=False)
        if expression.attr == "parent":
            base_state = _infer_path_expr_state(expression.value, scope)
            if base_state is None:
                return None
            return PathExprState(
                anchored=base_state.anchored,
                literal_path=_parent_literal_path(base_state.literal_path),
                uses_path_reference=base_state.uses_path_reference,
            )
        return None
    if isinstance(expression, ast.Subscript):
        if isinstance(expression.value, ast.Attribute) and expression.value.attr == "__path__":
            return PathExprState(anchored=True, literal_path=None, uses_path_reference=False)
        return None
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Div):
        left_state = _infer_path_expr_state(expression.left, scope)
        right_state = _infer_path_expr_state(expression.right, scope)
        if left_state is None and right_state is None:
            return None
        return PathExprState(
            anchored=False if left_state is None else left_state.anchored,
            literal_path=_join_literal_paths(
                None if left_state is None else left_state.literal_path,
                None if right_state is None else right_state.literal_path,
            ),
            uses_path_reference=(False if left_state is None else left_state.uses_path_reference)
            or (False if right_state is None else right_state.uses_path_reference),
        )
    if isinstance(expression, ast.Call):
        helper_name = _get_call_name(expression.func)
        if helper_name in PATH_REFERENCE_HELPERS:
            return PathExprState(anchored=True, literal_path=None, uses_path_reference=True)
        if helper_name == "Path":
            states = [_infer_path_expr_state(argument, scope) for argument in expression.args]
            filtered_states = [state for state in states if state is not None]
            if len(filtered_states) == 0:
                return None
            literal_path: str | None = None
            anchored = False
            uses_path_reference = False
            for state in filtered_states:
                literal_path = _join_literal_paths(literal_path, state.literal_path)
                anchored = anchored or state.anchored
                uses_path_reference = uses_path_reference or state.uses_path_reference
            return PathExprState(anchored=anchored, literal_path=literal_path, uses_path_reference=uses_path_reference)
        if isinstance(expression.func, ast.Attribute):
            base_state = _infer_path_expr_state(expression.func.value, scope)
            if base_state is None:
                return None
            if expression.func.attr in {"resolve", "absolute", "expanduser", "collapseuser"}:
                return base_state
            if expression.func.attr == "joinpath":
                literal_path = base_state.literal_path
                uses_path_reference = base_state.uses_path_reference
                for argument in expression.args:
                    argument_state = _infer_path_expr_state(argument, scope)
                    if argument_state is None:
                        continue
                    literal_path = _join_literal_paths(literal_path, argument_state.literal_path)
                    uses_path_reference = uses_path_reference or argument_state.uses_path_reference
                return PathExprState(
                    anchored=base_state.anchored,
                    literal_path=literal_path,
                    uses_path_reference=uses_path_reference,
                )
            if expression.func.attr == "with_name":
                argument_state = _infer_path_expr_state(expression.args[0], scope) if len(expression.args) == 1 else None
                return PathExprState(
                    anchored=base_state.anchored,
                    literal_path=None if argument_state is None else argument_state.literal_path,
                    uses_path_reference=base_state.uses_path_reference or (False if argument_state is None else argument_state.uses_path_reference),
                )
        return None
    return None


def _match_asset_candidate(
    candidate: str,
    anchored: bool,
    relative_asset_map: dict[str, AssetDefinition],
    unique_basenames: dict[str, AssetDefinition],
    top_level_dirs: frozenset[str],
) -> AssetDefinition | None:
    normalized_candidate = _normalize_path(candidate)
    if normalized_candidate in relative_asset_map:
        return relative_asset_map[normalized_candidate]
    first_segment = normalized_candidate.split("/", 1)[0]
    if "/" in normalized_candidate and (anchored or first_segment in top_level_dirs):
        matches = [
            asset
            for relative_path, asset in relative_asset_map.items()
            if relative_path.endswith(f"/{normalized_candidate}")
        ]
        if len(matches) == 1:
            return matches[0]
        return None
    if anchored:
        return unique_basenames.get(normalized_candidate)
    return None


def _scan_expr_tree(
    expression: ast.expr,
    scope: dict[str, PathExprState],
    python_file: Path,
    source: str,
    relative_asset_map: dict[str, AssetDefinition],
    unique_basenames: dict[str, AssetDefinition],
    top_level_dirs: frozenset[str],
    violations: list[PathReferenceViolation],
    seen: set[tuple[Path, int, str]],
) -> None:
    for node in ast.walk(expression):
        if not isinstance(node, ast.expr):
            continue
        state = _infer_path_expr_state(node, scope)
        if state is None or state.literal_path is None or state.uses_path_reference:
            continue
        asset = _match_asset_candidate(
            candidate=state.literal_path,
            anchored=state.anchored,
            relative_asset_map=relative_asset_map,
            unique_basenames=unique_basenames,
            top_level_dirs=top_level_dirs,
        )
        if asset is None:
            continue
        key = (python_file, node.lineno, asset.relative_path)
        if key in seen:
            continue
        seen.add(key)
        expression_text = ast.get_source_segment(source, node) or ast.unparse(node)
        violations.append(
            PathReferenceViolation(
                python_file=python_file,
                line_number=node.lineno,
                asset=asset,
                expression=expression_text,
            )
        )


def _scan_non_body_children(
    node: ast.AST,
    scope: dict[str, PathExprState],
    python_file: Path,
    source: str,
    relative_asset_map: dict[str, AssetDefinition],
    unique_basenames: dict[str, AssetDefinition],
    top_level_dirs: frozenset[str],
    violations: list[PathReferenceViolation],
    seen: set[tuple[Path, int, str]],
) -> None:
    for field_name, value in ast.iter_fields(node):
        if field_name in BODY_FIELD_NAMES:
            continue
        if isinstance(value, ast.expr):
            _scan_expr_tree(value, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
            continue
        if isinstance(value, list):
            for item in value:
                if isinstance(item, ast.expr):
                    _scan_expr_tree(item, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
                elif isinstance(item, ast.AST) and not isinstance(item, ast.stmt):
                    _scan_non_body_children(item, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
            continue
        if isinstance(value, ast.AST) and not isinstance(value, ast.stmt):
            _scan_non_body_children(value, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)


def _scan_body(
    body: list[ast.stmt],
    scope: dict[str, PathExprState],
    python_file: Path,
    source: str,
    relative_asset_map: dict[str, AssetDefinition],
    unique_basenames: dict[str, AssetDefinition],
    top_level_dirs: frozenset[str],
    violations: list[PathReferenceViolation],
    seen: set[tuple[Path, int, str]],
) -> None:
    local_scope = dict(scope)
    for statement in body:
        _scan_statement(
            statement=statement,
            scope=local_scope,
            python_file=python_file,
            source=source,
            relative_asset_map=relative_asset_map,
            unique_basenames=unique_basenames,
            top_level_dirs=top_level_dirs,
            violations=violations,
            seen=seen,
        )


def _scan_statement(
    statement: ast.stmt,
    scope: dict[str, PathExprState],
    python_file: Path,
    source: str,
    relative_asset_map: dict[str, AssetDefinition],
    unique_basenames: dict[str, AssetDefinition],
    top_level_dirs: frozenset[str],
    violations: list[PathReferenceViolation],
    seen: set[tuple[Path, int, str]],
) -> None:
    _scan_non_body_children(
        node=statement,
        scope=scope,
        python_file=python_file,
        source=source,
        relative_asset_map=relative_asset_map,
        unique_basenames=unique_basenames,
        top_level_dirs=top_level_dirs,
        violations=violations,
        seen=seen,
    )
    if isinstance(statement, ast.Assign):
        value_state = _infer_path_expr_state(statement.value, scope)
        for target in statement.targets:
            if isinstance(target, ast.Name) and value_state is not None:
                scope[target.id] = value_state
    elif isinstance(statement, ast.AnnAssign):
        value_state = _infer_path_expr_state(statement.value, scope) if statement.value is not None else None
        if isinstance(statement.target, ast.Name) and value_state is not None:
            scope[statement.target.id] = value_state
    if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        _scan_body(statement.body, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
    if isinstance(statement, ast.If | ast.For | ast.AsyncFor | ast.While):
        _scan_body(statement.body, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
        _scan_body(statement.orelse, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
    elif isinstance(statement, ast.With | ast.AsyncWith):
        _scan_body(statement.body, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
    elif isinstance(statement, ast.Try):
        _scan_body(statement.body, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
        _scan_body(statement.orelse, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
        _scan_body(statement.finalbody, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
        for handler in statement.handlers:
            _scan_body(handler.body, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
    elif isinstance(statement, ast.Match):
        for case in statement.cases:
            _scan_body(case.body, scope, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)


def _collect_path_reference_violations(assets: tuple[AssetDefinition, ...]) -> tuple[PathReferenceViolation, ...]:
    relative_asset_map = {asset.relative_path: asset for asset in assets}
    unique_basenames = _build_unique_basename_map(assets=assets)
    top_level_dirs = frozenset(relative_path.split("/", 1)[0] for relative_path in relative_asset_map)
    violations: list[PathReferenceViolation] = []
    seen: set[tuple[Path, int, str]] = set()
    python_files = sorted(
        path
        for path in REPO_ROOT.rglob("*.py")
        if ".venv" not in path.parts and "__pycache__" not in path.parts
    )
    for python_file in python_files:
        source = python_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=python_file.as_posix())
        _scan_body(tree.body, {}, python_file, source, relative_asset_map, unique_basenames, top_level_dirs, violations, seen)
    return tuple(sorted(violations, key=lambda item: (item.python_file.as_posix(), item.line_number, item.asset.relative_path)))


def _format_failures(failures: tuple[str, ...]) -> str:
    return "\n".join(failures)


def _format_violations(violations: tuple[PathReferenceViolation, ...]) -> str:
    lines: list[str] = []
    for violation in violations:
        lines.append(
            f"{violation.python_file.relative_to(REPO_ROOT).as_posix()}:{violation.line_number}: "
            f"use {violation.asset.variable_name} from {violation.asset.init_file.relative_to(REPO_ROOT).as_posix()} "
            f"for {violation.asset.relative_path}; found {violation.expression}"
        )
    return os.linesep.join(lines)


def test_all_non_py_assets_have_sibling_path_references() -> None:
    _assets, failures = _collect_assets()
    assert not failures, _format_failures(failures)


def test_python_files_use_sibling_path_references_for_non_py_assets() -> None:
    assets, failures = _collect_assets()
    assert not failures, _format_failures(failures)
    violations = _collect_path_reference_violations(assets)
    assert not violations, _format_violations(violations)
