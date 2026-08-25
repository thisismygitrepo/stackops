from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceKind
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import (
    present_resources,
    resource_candidate,
    scan_plugin_roots,
    scan_skill_roots,
)


@dataclass(frozen=True)
class DoctorPathCandidate:
    name: str
    origin: DoctorOrigin
    path: Path
    detail: str
    include_missing: bool
    is_mcp: bool


@dataclass(frozen=True)
class DoctorFileRoot:
    origin: DoctorOrigin
    root: Path
    patterns: tuple[str, ...]
    detail: str


def shared_skill_roots(*, context: DoctorContext) -> tuple[tuple[DoctorOrigin, Path, str], ...]:
    roots: list[tuple[DoctorOrigin, Path, str]] = [("global", context.home_directory / ".agents" / "skills", "shared user skill")]
    roots.extend(("local", directory / ".agents" / "skills", "shared project skill") for directory in context.ancestor_directories)
    return tuple(roots)


def _path_resources(*, kind: DoctorResourceKind, candidates: Sequence[DoctorPathCandidate]) -> tuple[DoctorResource, ...]:
    return present_resources(
        candidates=(
            resource_candidate(
                kind=kind,
                is_mcp=candidate.is_mcp,
                name=candidate.name,
                origin=candidate.origin,
                path=candidate.path,
                present_state="active",
                detail=candidate.detail,
                include_missing=candidate.include_missing,
            )
            for candidate in candidates
        )
    )


def _file_root_resources(*, kind: DoctorResourceKind, roots: Sequence[DoctorFileRoot]) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    seen_paths: set[Path] = set()
    for root in roots:
        if not root.root.is_dir():
            continue
        for pattern in root.patterns:
            for path in sorted(root.root.glob(pattern)):
                if not path.is_file():
                    continue
                resolved_path = path.resolve(strict=False)
                if resolved_path in seen_paths:
                    continue
                seen_paths.add(resolved_path)
                resources.append(
                    DoctorResource(
                        kind=kind,
                        is_mcp=False,
                        name=resolved_path.name,
                        origin=root.origin,
                        state="active",
                        path=resolved_path,
                        detail=root.detail,
                    )
                )
    return tuple(resources)


def collect_standard_resources(
    *,
    configurations: Sequence[DoctorPathCandidate],
    instructions: Sequence[DoctorPathCandidate],
    instruction_roots: Sequence[DoctorFileRoot],
    skill_roots: Sequence[tuple[DoctorOrigin, Path, str]],
    plugin_roots: Sequence[tuple[DoctorOrigin, Path, str]],
    plugin_patterns: Sequence[str],
) -> tuple[DoctorResource, ...]:
    return (
        *_path_resources(kind="configuration", candidates=configurations),
        *scan_plugin_roots(roots=plugin_roots, patterns=plugin_patterns, state="active"),
        *scan_skill_roots(roots=skill_roots, recursive=True, state="available"),
        *_path_resources(kind="instructions", candidates=instructions),
        *_file_root_resources(kind="instructions", roots=instruction_roots),
    )
