from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT.joinpath("src")


@dataclass(frozen=True, slots=True)
class PathReference:
    init_file: Path
    variable_name: str
    relative_path: str


@dataclass(frozen=True, slots=True)
class InvalidPathReference:
    init_file: Path
    variable_name: str
    reason: str


@dataclass(frozen=True, slots=True)
class MissingPathReference:
    init_file: Path
    variable_name: str
    relative_path: str
    resolved_path: Path


def _iter_init_files(src_root: Path) -> Iterator[Path]:
    yield from sorted(src_root.rglob("__init__.py"))


def _literal_string(value: ast.expr | None) -> str | None:
    if value is None:
        return None
    try:
        literal_value = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None
    if isinstance(literal_value, str):
        return literal_value
    return None


def _extract_path_references(init_file: Path) -> tuple[list[PathReference], list[InvalidPathReference]]:
    module = ast.parse(init_file.read_text(encoding="utf-8"), filename=init_file.as_posix())
    references: list[PathReference] = []
    invalid_references: list[InvalidPathReference] = []
    for statement in module.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if not isinstance(target, ast.Name):
                    continue
                if "_PATH_REFERENCE" not in target.id:
                    continue
                relative_path = _literal_string(statement.value)
                if relative_path is None:
                    invalid_references.append(
                        InvalidPathReference(
                            init_file=init_file,
                            variable_name=target.id,
                            reason="expected a literal string assignment",
                        )
                    )
                    continue
                references.append(
                    PathReference(
                        init_file=init_file,
                        variable_name=target.id,
                        relative_path=relative_path,
                    )
                )
        if isinstance(statement, ast.AnnAssign):
            if not isinstance(statement.target, ast.Name):
                continue
            if "_PATH_REFERENCE" not in statement.target.id:
                continue
            relative_path = _literal_string(statement.value)
            if relative_path is None:
                invalid_references.append(
                    InvalidPathReference(
                        init_file=init_file,
                        variable_name=statement.target.id,
                        reason="expected a literal string assignment",
                    )
                )
                continue
            references.append(
                PathReference(
                    init_file=init_file,
                    variable_name=statement.target.id,
                    relative_path=relative_path,
                )
            )
    return references, invalid_references


def _format_repo_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _build_failure_message(
    invalid_references: list[InvalidPathReference],
    missing_references: list[MissingPathReference],
) -> str:
    lines: list[str] = []
    if invalid_references:
        lines.append("Invalid _PATH_REFERENCE definitions:")
        for invalid_reference in invalid_references:
            lines.append(
                f"{_format_repo_relative(invalid_reference.init_file)}::{invalid_reference.variable_name}: {invalid_reference.reason}"
            )
    if missing_references:
        if lines:
            lines.append("")
        lines.append("Missing _PATH_REFERENCE targets:")
        for missing_reference in missing_references:
            lines.append(
                f"{_format_repo_relative(missing_reference.init_file)}::{missing_reference.variable_name} -> "
                f"{missing_reference.relative_path} -> {missing_reference.resolved_path.as_posix()}"
            )
    return "\n".join(lines)


def test_all_path_reference_targets_exist(capsys: pytest.CaptureFixture[str]) -> None:
    invalid_references: list[InvalidPathReference] = []
    missing_references: list[MissingPathReference] = []
    reference_count = 0
    for init_file in _iter_init_files(SRC_ROOT):
        references, invalid_items = _extract_path_references(init_file=init_file)
        invalid_references.extend(invalid_items)
        reference_count += len(references)
        for reference in references:
            resolved_path = init_file.parent.joinpath(reference.relative_path).resolve(strict=False)
            if resolved_path.exists():
                continue
            missing_references.append(
                MissingPathReference(
                    init_file=init_file,
                    variable_name=reference.variable_name,
                    relative_path=reference.relative_path,
                    resolved_path=resolved_path,
                )
            )
    with capsys.disabled():
        print(f"Picked up {reference_count} _PATH_REFERENCE variables.")
    if invalid_references or missing_references:
        pytest.fail(_build_failure_message(invalid_references=invalid_references, missing_references=missing_references))
