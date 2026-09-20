from pathlib import Path
from platform import system

from stackops.scripts.python.helpers.helpers_agents.agents_sandbox import resolve_sandbox_access
from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.scripts.python.helpers.helpers_agents.deepseek_launch import build_deepseek_command, deepseek_patch_paths, render_deepseek_prompt_command
from stackops.utils.sandbox.containers import build_container_command
from stackops.utils.sandbox.options import SandboxBackend
from stackops.utils.schemas.fire_agents.fire_agents_types import AI_SPEC


def fire_deepseek(*, ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    if ai_spec["model"] is not None or ai_spec["provider"] is not None:
        raise ValueError("DeepSeek selects its model and provider through settings.yaml or its web interface; CLI overrides are unsupported.")
    is_windows = system() == "Windows"
    container = ai_spec["machine"] == "docker"
    patch_paths = deepseek_patch_paths(directory=repo_root)
    command = build_deepseek_command(profile="headless", patch_paths=patch_paths, container=container, is_windows=is_windows)
    setup_lines: list[str] = []
    if container:
        access = resolve_sandbox_access(agent="deepseek")
        for directory in access.writable_paths:
            quoted = quote_for_shell(str(directory), is_windows=is_windows)
            setup_lines.append(
                f"""New-Item -ItemType Directory -Force -Path {quoted} | Out-Null""" if is_windows else f"""mkdir -p {quoted}"""
            )
        command = build_container_command(
            executable="docker", backend=SandboxBackend.DOCKER, image="statistician/stackops-ai:latest", command=command,
            directory=repo_root, access=access, read_only_paths=patch_paths, host_system=system(), interactive=False,
        )
    setup_lines.append(render_deepseek_prompt_command(command=command, prompt_file=prompt_path, is_windows=is_windows))
    return "\n".join(setup_lines)
