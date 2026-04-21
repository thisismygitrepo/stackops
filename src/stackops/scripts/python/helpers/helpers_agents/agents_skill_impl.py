from collections.abc import Sequence
from pathlib import Path
import shlex
from typing import Final, Literal, TypeAlias

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AGENTS

SKILL_INSTALL_SCOPE: TypeAlias = Literal["local", "global"]

_OPEN_SOURCE_SKILL_SOURCES: Final[dict[str, str]] = {
    "agent-browser": "vercel-labs/agent-browser",
    "caveman": "JuliusBrussee/caveman",
}

_SKILLS_CLI_AGENT_NAMES: Final[dict[AGENTS, str]] = {
    "auggie": "augment",
    "claude": "claude-code",
    "cline": "cline",
    "codex": "codex",
    "copilot": "github-copilot",
    "crush": "crush",
    "cursor-agent": "cursor",
    "droid": "droid",
    "gemini": "gemini-cli",
    "kilocode": "kilo",
    "opencode": "opencode",
    "pi": "pi",
    "qwen": "qwen-code",
    "warp-cli": "warp",
}


def is_supported_agent_skill_name(*, skill_name: str) -> bool:
    return skill_name in _OPEN_SOURCE_SKILL_SOURCES


def supported_agent_skill_names() -> tuple[str, ...]:
    return tuple(_OPEN_SOURCE_SKILL_SOURCES)


def supported_agent_skill_agents() -> tuple[AGENTS, ...]:
    return tuple(_SKILLS_CLI_AGENT_NAMES)


def resolve_agent_skill_install_root(*, directory: str | None) -> Path:
    if directory is not None:
        agent_dir = Path(directory).expanduser().resolve()
        if not agent_dir.is_dir():
            raise ValueError(f"Provided directory '{directory}' does not exist or is not a directory.")
        return agent_dir
    return Path.cwd()


def build_agent_skill_install_commands(
    *,
    skill_names: Sequence[str],
    agents: Sequence[AGENTS],
    scope: SKILL_INSTALL_SCOPE,
) -> tuple[tuple[str, ...], ...]:
    commands: list[tuple[str, ...]] = []
    for skill_name in skill_names:
        source = _OPEN_SOURCE_SKILL_SOURCES.get(skill_name)
        if source is None:
            raise ValueError(f"Skill '{skill_name}' is not recognized. Supported skills: {', '.join(supported_agent_skill_names())}")
        for agent in agents:
            skills_cli_agent_name = _SKILLS_CLI_AGENT_NAMES.get(agent)
            if skills_cli_agent_name is None:
                raise ValueError(
                    f"Skill '{skill_name}' cannot be installed for StackOps agent '{agent}' through the skills CLI. "
                    f"Supported StackOps agents: {', '.join(supported_agent_skill_agents())}"
                )

            command = ["npx", "skills", "add", source, "--agent", skills_cli_agent_name, "--yes"]
            if scope == "global":
                command.append("--global")
            commands.append(tuple(command))
    return tuple(commands)


def render_agent_skill_install_script(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> str:
    rendered_lines = [f"cd {shlex.quote(str(install_root))}"]
    rendered_lines.extend(" ".join(shlex.quote(part) for part in command) for command in commands)
    return "\n".join(rendered_lines) + "\n"


def run_agent_skill_install_commands(*, install_root: Path, commands: Sequence[tuple[str, ...]]) -> None:
    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(script=render_agent_skill_install_script(install_root=install_root, commands=commands), strict=False)


def add_skill(*, skill_name: str, agent: AGENTS, scope: SKILL_INSTALL_SCOPE, directory: str | None) -> None:
    install_root = resolve_agent_skill_install_root(directory=directory)
    commands = build_agent_skill_install_commands(skill_names=(skill_name,), agents=(agent,), scope=scope)
    run_agent_skill_install_commands(install_root=install_root, commands=commands)
