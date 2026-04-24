from collections.abc import Sequence
from pathlib import Path
import shlex
from typing import Final, Literal, TypeAlias

SKILL_INSTALL_SCOPE: TypeAlias = Literal["local", "global"]
SKILLS_CLI_PACKAGE: Final[str] = "skills@latest"

_OPEN_SOURCE_SKILL_SOURCES: Final[dict[str, str]] = {
    "agent-browser": "vercel-labs/agent-browser",
    "caveman": "JuliusBrussee/caveman",
    "grill-me": "mattpocock/skills/grill-me",
}


def is_supported_agent_skill_name(*, skill_name: str) -> bool:
    return skill_name in _OPEN_SOURCE_SKILL_SOURCES


def supported_agent_skill_names() -> tuple[str, ...]:
    return tuple(_OPEN_SOURCE_SKILL_SOURCES)


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
    *, skill_names: Sequence[str], agent_targets: Sequence[str], scope: SKILL_INSTALL_SCOPE
) -> tuple[tuple[str, ...], ...]:
    commands: list[tuple[str, ...]] = []
    for skill_name in skill_names:
        source = _OPEN_SOURCE_SKILL_SOURCES.get(skill_name)
        if source is None:
            raise ValueError(f"Skill '{skill_name}' is not recognized. Supported skills: {', '.join(supported_agent_skill_names())}")

        command = ["bunx", SKILLS_CLI_PACKAGE, "add", source, "--yes"]
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


def run_agent_skill_install_commands(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> None:
    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(script=render_agent_skill_install_script(install_root=install_root, commands=commands), strict=False)


def add_skill(*, skill_name: str, agent: str | None, scope: SKILL_INSTALL_SCOPE, directory: str | None) -> None:
    install_root = resolve_agent_skill_install_root(directory=directory)
    agent_targets = parse_requested_skill_agent_targets(raw_value=agent)
    commands = build_agent_skill_install_commands(skill_names=(skill_name,), agent_targets=agent_targets, scope=scope)
    run_agent_skill_install_commands(install_root=install_root, commands=commands)
