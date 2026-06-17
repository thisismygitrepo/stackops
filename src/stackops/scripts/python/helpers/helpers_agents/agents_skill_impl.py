from collections.abc import Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
from typing import Final, Literal, TypeAlias

SKILL_INSTALL_SCOPE: TypeAlias = Literal["local", "global"]
SKILL_INSTALL_COMMAND_BACKEND: TypeAlias = Literal["bunx", "npx"]
SKILL_INSTALL_BACKEND: TypeAlias = Literal["bunx", "npx", "stackops", "s"]
RESOLVED_SKILL_INSTALL_BACKEND: TypeAlias = Literal["bunx", "npx", "stackops"]
SKILLS_CLI_PACKAGE: Final[str] = "skills@latest"
AGENT_SKILL_PREVIEW_SIZE_PERCENT: Final[float] = 70.0


@dataclass(frozen=True)
class AgentSkillSource:
    source: str
    skill: str | None = None


_OPEN_SOURCE_SKILL_SOURCES: Final[dict[str, AgentSkillSource]] = {
    "agent-browser": AgentSkillSource("vercel-labs/agent-browser"),
    "agent-skills": AgentSkillSource("addyosmani/agent-skills"),
    "caveman": AgentSkillSource("JuliusBrussee/caveman", skill="caveman"),
    "grill-me": AgentSkillSource("mattpocock/skills/grill-me"),
    "last30days": AgentSkillSource("mvanhorn/last30days-skill"),
    "stackops": AgentSkillSource("https://github.com/thisismygitrepo/stackops", skill="stackops"),
    "workflows": AgentSkillSource("https://github.com/thisismygitrepo/stackops", skill="workflows"),
}


def is_supported_agent_skill_name(*, skill_name: str) -> bool:
    return skill_name in _OPEN_SOURCE_SKILL_SOURCES


def supported_agent_skill_names() -> tuple[str, ...]:
    return tuple(_OPEN_SOURCE_SKILL_SOURCES)


def resolve_agent_skill_install_backend(*, backend: SKILL_INSTALL_BACKEND) -> RESOLVED_SKILL_INSTALL_BACKEND:
    if backend == "s":
        return "stackops"
    if backend in ("bunx", "npx", "stackops"):
        return backend
    raise ValueError("Unsupported skill install backend. Use bunx, npx, stackops, or s.")


def build_stackops_skill_folder_names() -> dict[str, str]:
    return {skill_name: source.skill or skill_name for skill_name, source in _OPEN_SOURCE_SKILL_SOURCES.items()}


def build_agent_skill_preview_mapping() -> dict[str, str]:
    preview_mapping: dict[str, str] = {}
    for skill_name, source in _OPEN_SOURCE_SKILL_SOURCES.items():
        preview_mapping[skill_name] = json.dumps(
            {
                "type": "agent-skill",
                "name": skill_name,
                "source": source.source,
                "skill": source.skill,
            },
            indent=2,
        )
    return preview_mapping


def choose_requested_skill_names() -> tuple[str, ...]:
    from stackops.utils.options_utils import tv_options

    selection = tv_options.choose_from_dict_with_preview(
        options_to_preview_mapping=build_agent_skill_preview_mapping(),
        extension="json",
        multi=True,
        preview_size_percent=AGENT_SKILL_PREVIEW_SIZE_PERCENT,
    )
    if len(selection) == 0:
        raise ValueError("Selection cancelled for agent skill")
    return tuple(selection)


def parse_requested_skill_names(*, raw_value: str) -> tuple[str, ...]:
    if raw_value.strip() == "":
        raise ValueError("Provide at least one skill name")

    parts = [part.strip() for part in raw_value.split(",")]
    if any(part == "" for part in parts):
        raise ValueError("Skill names must be a comma-separated list without empty entries")

    seen: set[str] = set()
    duplicates: list[str] = []
    for part in parts:
        if part in seen:
            duplicates.append(part)
            continue
        seen.add(part)
    if len(duplicates) > 0:
        raise ValueError(f"Duplicate skill names are not allowed: {', '.join(dict.fromkeys(duplicates))}")

    return tuple(parts)


def resolve_agent_skill_install_root(*, directory: str | None) -> Path:
    if directory is not None:
        agent_dir = Path(directory).expanduser().resolve()
        if not agent_dir.is_dir():
            raise ValueError(f"Provided directory '{directory}' does not exist or is not a directory.")
        return agent_dir
    return Path.cwd()


def parse_requested_skill_agent_targets(*, raw_value: str | None) -> tuple[str, ...]:
    if raw_value is None:
        return ()
    if raw_value.strip() == "":
        return ()
    parts = tuple(part.strip() for part in raw_value.split(","))
    if any(part == "" for part in parts):
        raise ValueError("Agent targets must be a comma-separated list without empty entries")
    return parts


def build_agent_skill_install_commands(
    *,
    skill_names: Sequence[str],
    agent_targets: Sequence[str],
    scope: SKILL_INSTALL_SCOPE,
    backend: SKILL_INSTALL_COMMAND_BACKEND,
    yes: bool,
) -> tuple[tuple[str, ...], ...]:
    commands: list[tuple[str, ...]] = []
    for skill_name in skill_names:
        source = _OPEN_SOURCE_SKILL_SOURCES.get(skill_name)
        if source is None:
            raise ValueError(f"Skill '{skill_name}' is not recognized. Supported skills: {', '.join(supported_agent_skill_names())}")

        command = [backend, SKILLS_CLI_PACKAGE, "add", source.source]
        if source.skill is not None:
            command.extend(("--skill", source.skill))
        if yes:
            command.append("--yes")
        if scope == "global":
            command.append("--global")
        if len(agent_targets) > 0:
            command.append("--agent")
            command.extend(agent_targets)
        commands.append(tuple(command))
    return tuple(commands)


def render_agent_skill_install_script(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> str:
    rendered_lines = [f"cd {shlex.quote(str(install_root))}"]
    rendered_lines.extend(" ".join(shlex.quote(part) for part in command) for command in commands)
    return "\n".join(rendered_lines) + "\n"


def run_agent_skill_install_commands(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> int:
    import os

    from stackops.utils.code import exit_then_run_shell_script, run_shell_script

    script = render_agent_skill_install_script(install_root=install_root, commands=commands)
    op_program_path_raw = os.environ.get("OP_PROGRAM_PATH")
    if op_program_path_raw is not None and not Path(op_program_path_raw).exists():
        exit_then_run_shell_script(script=script, strict=False)
    proc = run_shell_script(script=script, display_script=True, clean_env=False)
    return proc.returncode


def add_skill(
    *,
    skill_name: str | None,
    agent: str | None,
    scope: SKILL_INSTALL_SCOPE,
    directory: str | None,
    backend: SKILL_INSTALL_BACKEND,
    yes: bool,
) -> int:
    install_root = resolve_agent_skill_install_root(directory=directory)
    agent_targets = parse_requested_skill_agent_targets(raw_value=agent)
    resolved_skill_names = choose_requested_skill_names() if skill_name is None else parse_requested_skill_names(raw_value=skill_name)
    resolved_backend = resolve_agent_skill_install_backend(backend=backend)
    if resolved_backend == "stackops":
        from stackops.scripts.python.helpers.helpers_agents import agents_skill_stackops_backend

        results = agents_skill_stackops_backend.install_stackops_agent_skills(
            skill_names=resolved_skill_names,
            skill_folder_names=build_stackops_skill_folder_names(),
            install_root=install_root,
            scope=scope,
        )
        agents_skill_stackops_backend.print_stackops_agent_skill_install_summary(results=results)
        return 0

    commands = build_agent_skill_install_commands(
        skill_names=resolved_skill_names,
        agent_targets=agent_targets,
        scope=scope,
        backend=resolved_backend,
        yes=yes,
    )
    return run_agent_skill_install_commands(install_root=install_root, commands=commands)
