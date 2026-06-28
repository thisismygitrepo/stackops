"""Direct-copy backend for StackOps-bundled agent skills."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Final, Literal, TypeAlias

from rich.console import Console

from stackops.utils.accessories import get_repo_root

STACKOPS_SKILL_INSTALL_SCOPE: TypeAlias = Literal["local", "global"]

AGENT_SKILLS_DIRECTORY_PARTS: Final[tuple[str, str]] = (".agents", "skills")
SKILL_FILE_NAME: Final[str] = "SKILL.md"


@dataclass(frozen=True)
class StackopsAgentSkillInstallResult:
    skill_name: str
    source_path: Path
    target_path: Path


class StackopsAgentSkillBackendError(ValueError):
    pass


def _dedupe_paths(paths: Sequence[Path]) -> tuple[Path, ...]:
    seen: set[Path] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = path.expanduser().resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return tuple(deduped)


def _candidate_source_roots() -> tuple[Path, ...]:
    module_path = Path(__file__).resolve()
    candidates: list[Path] = [parent / "skills" for parent in module_path.parents]

    cwd = Path.cwd().resolve(strict=False)
    candidates.append(cwd / "skills")
    cwd_repo_root = get_repo_root(cwd)
    if cwd_repo_root is not None:
        candidates.append(cwd_repo_root / "skills")

    return _dedupe_paths(candidates)


def _contains_agent_skills(path: Path) -> bool:
    if not path.is_dir():
        return False
    try:
        children = tuple(path.iterdir())
    except OSError:
        return False
    return any(child.is_dir() and child.joinpath(SKILL_FILE_NAME).is_file() for child in children)


def resolve_stackops_agent_skill_source_root(*, source_root: Path | None = None) -> Path:
    if source_root is not None:
        resolved_source_root = source_root.expanduser().resolve(strict=False)
        if not _contains_agent_skills(resolved_source_root):
            raise StackopsAgentSkillBackendError(f"StackOps skill source root does not contain skill directories: {resolved_source_root}")
        return resolved_source_root

    for candidate in _candidate_source_roots():
        if _contains_agent_skills(candidate):
            return candidate

    searched = ", ".join(str(candidate) for candidate in _candidate_source_roots())
    raise StackopsAgentSkillBackendError(f"StackOps skill source root was not found. Searched: {searched}")


def resolve_stackops_agent_skill_target_root(*, install_root: Path, scope: STACKOPS_SKILL_INSTALL_SCOPE) -> Path:
    if scope == "global":
        raise StackopsAgentSkillBackendError(
            "StackOps skill backend only supports --scope local. Use --backend bunx or --backend npx for global installs."
        )

    repo_root = get_repo_root(install_root)
    resolved_install_root = (repo_root if repo_root is not None else install_root).expanduser().resolve(strict=False)
    return resolved_install_root.joinpath(*AGENT_SKILLS_DIRECTORY_PARTS)


def _copy_skill_directory(*, source_path: Path, target_path: Path) -> None:
    if target_path.exists() and not target_path.is_dir():
        raise StackopsAgentSkillBackendError(f"Cannot install skill because target exists and is not a directory: {target_path}")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_path, target_path, dirs_exist_ok=True)


def _resolve_stackops_agent_skill_install_plans(
    *,
    skill_names: Sequence[str],
    skill_folder_names: Mapping[str, str],
    resolved_source_root: Path,
    target_root: Path,
) -> tuple[StackopsAgentSkillInstallResult, ...]:
    plans: list[StackopsAgentSkillInstallResult] = []
    for skill_name in skill_names:
        skill_folder_name = skill_folder_names.get(skill_name)
        if skill_folder_name is None:
            raise StackopsAgentSkillBackendError(f"Skill '{skill_name}' is not recognized. Supported skills: {', '.join(skill_folder_names)}")

        source_path = resolved_source_root / skill_folder_name
        if not source_path.joinpath(SKILL_FILE_NAME).is_file():
            raise StackopsAgentSkillBackendError(
                f"Skill '{skill_name}' is not bundled with the StackOps backend. "
                "Use --backend bunx or --backend npx for this alias."
            )

        target_path = target_root / skill_folder_name
        if target_path.exists() and not target_path.is_dir():
            raise StackopsAgentSkillBackendError(f"Cannot install skill because target exists and is not a directory: {target_path}")
        plans.append(StackopsAgentSkillInstallResult(skill_name=skill_name, source_path=source_path, target_path=target_path))

    return tuple(plans)


def install_stackops_agent_skills(
    *,
    skill_names: Sequence[str],
    skill_folder_names: Mapping[str, str],
    install_root: Path,
    scope: STACKOPS_SKILL_INSTALL_SCOPE,
    source_root: Path | None = None,
) -> tuple[StackopsAgentSkillInstallResult, ...]:
    resolved_source_root = resolve_stackops_agent_skill_source_root(source_root=source_root)
    target_root = resolve_stackops_agent_skill_target_root(install_root=install_root, scope=scope)
    plans = _resolve_stackops_agent_skill_install_plans(
        skill_names=skill_names,
        skill_folder_names=skill_folder_names,
        resolved_source_root=resolved_source_root,
        target_root=target_root,
    )

    for plan in plans:
        _copy_skill_directory(source_path=plan.source_path, target_path=plan.target_path)

    return plans


def print_stackops_agent_skill_install_summary(*, results: Sequence[StackopsAgentSkillInstallResult], console: Console | None = None) -> None:
    from rich import box
    from rich.table import Table

    table = Table(title="StackOps Skill Install", box=box.SIMPLE_HEAVY, header_style="bold cyan", show_lines=False, expand=False)
    table.add_column("Skill", style="bold")
    table.add_column("Path")
    table.add_column("Location", overflow="fold")
    table.add_column("Status", style="green")

    for result in results:
        table.add_row(
            result.skill_name,
            "source",
            str(result.source_path),
            "copied",
        )
        table.add_row(
            result.skill_name,
            "target",
            str(result.target_path),
            "copied",
        )

    output_console = console if console is not None else Console()
    output_console.print(table)
