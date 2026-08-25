from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext, DoctorOrigin, DoctorResource
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.scanning import scan_skill_roots


def _loose_skills(*, origin: DoctorOrigin, root: Path, detail: str) -> tuple[DoctorResource, ...]:
    if not root.is_dir():
        return ()
    return tuple(
        DoctorResource(kind="skill", name=path.stem, origin=origin, state="active", path=path.resolve(strict=False), detail=detail)
        for path in sorted(root.glob("*.md"))
        if path.name != "SKILL.md"
    )


def _skills(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    local_pi_root = context.working_directory / ".pi" / "skills"
    project_agents_roots: tuple[tuple[DoctorOrigin, Path, str], ...] = tuple(
        ("local", directory / ".agents" / "skills", "Project .agents skill discovered by Pi") for directory in reversed(context.ancestor_directories)
    )
    roots: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("local", local_pi_root, "Project .pi skill discovered by Pi"),
        *project_agents_roots,
        ("global", context.pi_home / "skills", "Global Pi skill"),
        ("global", context.home_directory / ".agents" / "skills", "Shared global Agent Skill"),
    )
    structured = scan_skill_roots(roots=roots, recursive=True, state="active")
    loose = (
        *_loose_skills(origin="local", root=local_pi_root, detail="Loose project .pi skill"),
        *_loose_skills(origin="global", root=context.pi_home / "skills", detail="Loose global Pi skill"),
    )
    return (*structured, *loose)


def _context_instructions(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    locations: tuple[tuple[DoctorOrigin, Path, str], ...] = (
        ("global", context.pi_home, "Global Pi context"),
        *(("local", directory, "Project context loaded from repository ancestry") for directory in context.ancestor_directories),
    )
    names = ("AGENTS.md", "AGENTS.MD", "CLAUDE.md", "CLAUDE.MD")
    for origin, directory, detail in locations:
        matches = tuple(directory / name for name in names if (directory / name).is_file())
        for index, path in enumerate(matches):
            resources.append(
                DoctorResource(
                    kind="instructions",
                    name=path.name,
                    origin=origin,
                    state="active" if index == 0 else "shadowed",
                    path=path.resolve(strict=False),
                    detail=detail,
                )
            )
    return tuple(resources)


def _system_instructions(*, context: DoctorContext) -> tuple[DoctorResource, ...]:
    resources: list[DoctorResource] = []
    local_root = context.working_directory / ".pi"
    for name, behavior in (("SYSTEM.md", "replaces Pi's default system prompt"), ("APPEND_SYSTEM.md", "appends to Pi's default system prompt")):
        local_path = local_root / name
        global_path = context.pi_home / name
        if local_path.is_file():
            resources.append(
                DoctorResource(
                    kind="instructions",
                    name=name,
                    origin="local",
                    state="active",
                    path=local_path.resolve(strict=False),
                    detail=f"Project file {behavior}",
                )
            )
        if global_path.is_file():
            resources.append(
                DoctorResource(
                    kind="instructions",
                    name=name,
                    origin="global",
                    state="shadowed" if local_path.is_file() else "active",
                    path=global_path.resolve(strict=False),
                    detail=f"Global file {behavior}",
                )
            )
    return tuple(resources)


def collect_pi_context_resources(context: DoctorContext) -> tuple[DoctorResource, ...]:
    return (*_skills(context=context), *_context_instructions(context=context), *_system_instructions(context=context))
