from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource, DoctorResourceState
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import scan_skill_roots


_ADMIN_SKILLS_PATH: Final[Path] = Path("/etc/codex/skills")


def _directory_instructions(*, directory: Path, origin: DoctorOrigin, names: tuple[str, ...], detail: str) -> tuple[DoctorResource, ...]:
    candidates = tuple(directory / name for name in dict.fromkeys(names))
    existing = tuple(path.resolve(strict=False) for path in candidates if path.is_file())
    active_path = next((path for path in existing if path.stat().st_size > 0), None)
    resources: list[DoctorResource] = []
    for path in existing:
        if path == active_path:
            state: DoctorResourceState = "active"
            selection_detail = "selected as this directory's instruction layer"
        elif path.stat().st_size == 0:
            state = "shadowed"
            selection_detail = "empty, so Codex skips it"
        else:
            state = "shadowed"
            selection_detail = f"lower filename precedence than {active_path.name}" if active_path is not None else "not selected"
        resources.append(
            DoctorResource(kind="instructions", name=path.name, origin=origin, state=state, path=path, detail=f"{detail}; {selection_detail}")
        )
    return tuple(resources)


def instruction_resources(*, context: DoctorContext, fallback_names: tuple[str, ...]) -> tuple[DoctorResource, ...]:
    resources = list(
        _directory_instructions(
            directory=context.codex_home,
            origin="global",
            names=("AGENTS.override.md", "AGENTS.md"),
            detail="global instruction scope; only the first non-empty candidate is used",
        )
    )
    project_names = ("AGENTS.override.md", "AGENTS.md", *fallback_names)
    layer_count = len(context.ancestor_directories)
    for layer_number, directory in enumerate(context.ancestor_directories, start=1):
        resources.extend(
            _directory_instructions(
                directory=directory,
                origin="local",
                names=project_names,
                detail=(f"project instruction layer {layer_number}/{layer_count}; active layers merge from project root to working directory"),
            )
        )
    return tuple(resources)


def skill_resources(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    roots: list[tuple[DoctorOrigin, Path, str]] = [
        ("local", directory / ".agents" / "skills", "repository skill available to Codex") for directory in context.ancestor_directories
    ]
    roots.extend(
        (
            ("global", context.home_directory / ".agents" / "skills", "user skill from the shared agent-skills location"),
            ("global", context.codex_home / "skills", "user skill from CODEX_HOME"),
            ("admin", _ADMIN_SKILLS_PATH, "administrator-provided Codex skill"),
            ("system", context.codex_home / "skills" / ".system", "system skill bundled with Codex"),
        )
    )
    return scan_skill_roots(roots=roots, recursive=False, state="available")
