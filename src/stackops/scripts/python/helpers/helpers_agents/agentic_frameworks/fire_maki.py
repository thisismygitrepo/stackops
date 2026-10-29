from pathlib import Path
from platform import system

from stackops.scripts.python.helpers.helpers_agents.agents_sandbox import resolve_sandbox_access
from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.scripts.python.helpers.helpers_agents.maki_launch import build_maki_command, render_maki_prompt_command
from stackops.utils.sandbox.containers import build_container_command
from stackops.utils.sandbox.options import SandboxBackend
from stackops.utils.schemas.fire_agents.fire_agents_types import AI_SPEC


def fire_maki(*, ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    is_windows = system() == "Windows"
    command = build_maki_command(model=ai_spec["model"], provider=ai_spec["provider"])
    setup_lines: list[str] = []
    if ai_spec["machine"] == "docker":
        access = resolve_sandbox_access(agent="maki")
        for directory in access.writable_paths:
            quoted = quote_for_shell(str(directory), is_windows=is_windows)
            setup_lines.append(
                f"""New-Item -ItemType Directory -Force -Path {quoted} | Out-Null""" if is_windows else f"""mkdir -p {quoted}"""
            )
        command.append("--trust")
        command = build_container_command(
            executable="docker", backend=SandboxBackend.DOCKER, image="statistician/stackops-ai:latest", command=command,
            directory=repo_root, access=access, read_only_paths=(), host_system=system(), interactive=False,
        )
    setup_lines.append(render_maki_prompt_command(command=command, prompt_file=prompt_path, is_windows=is_windows))
    return "\n".join(setup_lines)
