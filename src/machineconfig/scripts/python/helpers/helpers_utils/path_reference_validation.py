from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from machineconfig.utils.accessories import get_repo_root


EXCLUDED_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".ai",
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "site-packages",
    }
)


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


@dataclass(frozen=True, slots=True)
class PathReferenceAudit:
    repo_root: Path
    search_root: Path
    scanned_init_files: int
    reference_count: int
    invalid_references: tuple[InvalidPathReference, ...]
    missing_references: tuple[MissingPathReference, ...]

    def has_failures(self) -> bool:
        return len(self.invalid_references) > 0 or len(self.missing_references) > 0

    def invalid_count(self) -> int:
        return len(self.invalid_references)

    def missing_count(self) -> int:
        return len(self.missing_references)

    def resolved_reference_count(self) -> int:
        return self.reference_count - self.missing_count()


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


def _iter_init_files(search_root: Path) -> Iterator[Path]:
    for init_file in sorted(search_root.rglob("__init__.py")):
        relative_parts = init_file.relative_to(search_root).parts[:-1]
        if any(part in EXCLUDED_DIR_NAMES for part in relative_parts):
            continue
        yield init_file


def _format_repo_relative(*, path: Path, repo_root: Path) -> str:
    resolved_path = path.resolve(strict=False)
    resolved_repo_root = repo_root.resolve(strict=False)
    try:
        return resolved_path.relative_to(resolved_repo_root).as_posix()
    except ValueError:
        return resolved_path.as_posix()


def build_reference_test_console() -> Console:
    return Console()


def _build_reference_test_summary_table(*, audit: PathReferenceAudit) -> Table:
    table = Table(box=None, show_header=False, pad_edge=False)
    table.add_column("Field", style="bold cyan")
    table.add_column("Value", style="white")
    table.add_row("📦 Repository", str(audit.repo_root))
    table.add_row("🔎 Search Root", str(audit.search_root))
    table.add_row("🧭 Packages", str(audit.scanned_init_files))
    table.add_row("🔗 Declared Targets", str(audit.reference_count))
    table.add_row("✅ Resolved Targets", str(audit.resolved_reference_count()))
    table.add_row("⚠ Invalid Definitions", str(audit.invalid_count()))
    table.add_row("❌ Missing Targets", str(audit.missing_count()))
    return table


def _build_invalid_reference_table(*, audit: PathReferenceAudit) -> Table | None:
    if audit.invalid_count() == 0:
        return None
    table = Table(title="⚠ Invalid Definitions", header_style="bold yellow")
    table.add_column("File", style="cyan")
    table.add_column("Variable", style="magenta")
    table.add_column("Reason", style="white")
    for invalid_reference in audit.invalid_references:
        table.add_row(
            _format_repo_relative(path=invalid_reference.init_file, repo_root=audit.repo_root),
            invalid_reference.variable_name,
            invalid_reference.reason,
        )
    return table


def _build_missing_reference_table(*, audit: PathReferenceAudit) -> Table | None:
    if audit.missing_count() == 0:
        return None
    table = Table(title="❌ Missing Targets", header_style="bold red")
    table.add_column("File", style="cyan")
    table.add_column("Variable", style="magenta")
    table.add_column("Target", style="yellow")
    table.add_column("Resolved Path", style="white")
    for missing_reference in audit.missing_references:
        table.add_row(
            _format_repo_relative(path=missing_reference.init_file, repo_root=audit.repo_root),
            missing_reference.variable_name,
            missing_reference.relative_path,
            missing_reference.resolved_path.as_posix(),
        )
    return table


def print_reference_test_summary(*, console: Console, audit: PathReferenceAudit) -> None:
    title = "✅ Reference Audit Passed" if not audit.has_failures() else "❌ Reference Audit Failed"
    border_style = "green" if not audit.has_failures() else "red"
    console.print(Panel(_build_reference_test_summary_table(audit=audit), title=title, border_style=border_style, expand=False))


def print_reference_test_verbose_details(*, console: Console, audit: PathReferenceAudit) -> None:
    excluded_directories = ", ".join(sorted(EXCLUDED_DIR_NAMES))
    console.print(Panel(excluded_directories, title="🧹 Excluded Directories", border_style="blue", expand=False))

    invalid_table = _build_invalid_reference_table(audit=audit)
    if invalid_table is None:
        console.print(Panel("✅ No invalid _PATH_REFERENCE definitions found.", title="⚠ Invalid Definitions", border_style="green", expand=False))
    else:
        console.print(invalid_table)

    missing_table = _build_missing_reference_table(audit=audit)
    if missing_table is None:
        console.print(Panel("✅ No missing _PATH_REFERENCE targets found.", title="❌ Missing Targets", border_style="green", expand=False))
    else:
        console.print(missing_table)


def resolve_repo_root(*, repo_path: Path) -> Path:
    resolved_path = repo_path.expanduser().resolve(strict=False)
    if not resolved_path.exists():
        raise ValueError(f"repository path does not exist: {resolved_path}")
    detected_repo_root = get_repo_root(resolved_path)
    if detected_repo_root is not None:
        return detected_repo_root.resolve(strict=False)
    if resolved_path.is_file():
        return resolved_path.parent
    return resolved_path


def resolve_search_root(*, repo_root: Path, search_root: Path | None) -> Path:
    candidate = repo_root.joinpath("src") if search_root is None and repo_root.joinpath("src").is_dir() else repo_root
    if search_root is not None:
        candidate = search_root if search_root.is_absolute() else repo_root.joinpath(search_root)
    resolved_candidate = candidate.expanduser().resolve(strict=False)
    if not resolved_candidate.exists():
        raise ValueError(f"search root does not exist: {resolved_candidate}")
    if not resolved_candidate.is_dir():
        raise ValueError(f"search root is not a directory: {resolved_candidate}")
    return resolved_candidate


def audit_repository_path_references(*, repo_path: Path, search_root: Path | None) -> PathReferenceAudit:
    repo_root = resolve_repo_root(repo_path=repo_path)
    resolved_search_root = resolve_search_root(repo_root=repo_root, search_root=search_root)
    invalid_references: list[InvalidPathReference] = []
    missing_references: list[MissingPathReference] = []
    scanned_init_files = 0
    reference_count = 0
    for init_file in _iter_init_files(search_root=resolved_search_root):
        scanned_init_files += 1
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
    return PathReferenceAudit(
        repo_root=repo_root,
        search_root=resolved_search_root,
        scanned_init_files=scanned_init_files,
        reference_count=reference_count,
        invalid_references=tuple(invalid_references),
        missing_references=tuple(missing_references),
    )


def format_path_reference_audit(*, audit: PathReferenceAudit) -> str:
    lines: list[str] = []
    if len(audit.invalid_references) > 0:
        lines.append("Invalid _PATH_REFERENCE definitions:")
        for invalid_reference in audit.invalid_references:
            lines.append(
                f"{_format_repo_relative(path=invalid_reference.init_file, repo_root=audit.repo_root)}::{invalid_reference.variable_name}: {invalid_reference.reason}"
            )
    if len(audit.missing_references) > 0:
        if len(lines) > 0:
            lines.append("")
        lines.append("Missing _PATH_REFERENCE targets:")
        for missing_reference in audit.missing_references:
            lines.append(
                f"{_format_repo_relative(path=missing_reference.init_file, repo_root=audit.repo_root)}::{missing_reference.variable_name} -> "
                f"{missing_reference.relative_path} -> {missing_reference.resolved_path.as_posix()}"
            )
    return "\n".join(lines)
