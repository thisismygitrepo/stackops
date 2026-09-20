import os
import shlex
import sys
from pathlib import Path
from platform import system

from stackops.scripts.python.helpers.helpers_agents.agents_sandbox import resolve_sandbox_access
from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import (
    ReasoningEffort,
    copilot_reasoning_args,
    normalize_reasoning_effort,
)
from stackops.utils.sandbox.containers import container_path
from stackops.utils.sandbox.launch import build_sandbox_command, validate_sandbox_options
from stackops.utils.sandbox.options import SandboxAccess, SandboxBackend, SandboxOptions
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


def validate_prompt_sandbox(*, agent: AGENTS, options: SandboxOptions) -> None:
    validate_sandbox_options(options)
    if options.backend == SandboxBackend.NONE:
        return
    container = options.backend in (SandboxBackend.DOCKER, SandboxBackend.PODMAN)
    if agent == "q" and system() == "Windows" and not container:
        raise ValueError("Amazon Q requires WSL on Windows. Run agents inside WSL2 or select a Linux container sandbox.")
    if agent == "oz" and container and not os.environ.get("WARP_API_KEY"):
        raise ValueError("Containerized oz requires WARP_API_KEY; host Warp keychain authentication is unavailable inside the container.")


def build_sandboxed_prompt_script(
    *,
    agent: AGENTS,
    prompt_file: Path,
    reasoning_effort: ReasoningEffort | None,
    options: SandboxOptions,
) -> str:
    validate_prompt_sandbox(agent=agent, options=options)
    is_windows = system() == "Windows"
    container = options.backend in (SandboxBackend.DOCKER, SandboxBackend.PODMAN)
    reasoning = normalize_reasoning_effort(agent=agent, reasoning_effort=reasoning_effort)
    access = resolve_sandbox_access(agent=agent)
    input_paths: list[Path] = []
    prompt_text = ""
    prompt_argument = ""
    if agent in ("crush", "qwen", "droid"):
        input_paths.append(prompt_file)
        prompt_argument = container_path(prompt_file, is_windows=is_windows) if container else str(prompt_file)
    elif agent != "codex":
        prompt_text = prompt_file.read_text(encoding="utf-8")

    match agent:
        case "codex":
            command = [agent, "exec", "--dangerously-bypass-approvals-and-sandbox"]
            if reasoning is not None:
                command.extend(["-c", f'''model_reasoning_effort="{reasoning}"'''])
            command.append("-")
        case "copilot":
            command = [agent, *copilot_reasoning_args(reasoning_effort=reasoning), "-p", prompt_text, "--yolo"]
        case "deepseek":
            from stackops.scripts.python.helpers.helpers_agents.deepseek_launch import build_deepseek_command, deepseek_patch_paths

            patch_paths = deepseek_patch_paths(directory=Path.cwd())
            input_paths.extend(patch_paths)
            command = build_deepseek_command(profile="headless", patch_paths=patch_paths, container=container, is_windows=is_windows)
            command.extend(["--", "--", prompt_text])
        case "pi":
            command = [agent, "--mode", "json"]
            if reasoning is not None:
                command.extend(["--thinking", "off" if reasoning == "none" else reasoning])
            command.extend(["-p", prompt_text])
        case "agy":
            command = [agent, "--print", "--dangerously-skip-permissions", prompt_text]
        case "forge" | "claude":
            command = [agent, "-p", prompt_text]
        case "crush":
            command = [agent, "run", prompt_argument]
        case "qwen":
            command = [agent, "--yolo", "--prompt", prompt_argument]
        case "q":
            command = [agent, "chat", prompt_text]
        case "opencode":
            command = [agent, "run", prompt_text]
        case "kilocode":
            command = [agent, prompt_text]
        case "cline":
            from stackops.scripts.python.helpers.helpers_agents.mcp_install import resolve_agent_launch_prefix
            from stackops.utils.accessories import get_repo_root

            prefix = resolve_agent_launch_prefix(agent=agent, repo_root=get_repo_root(Path.cwd()))
            if prefix:
                config_directory = Path(prefix[1])
                access = SandboxAccess(
                    writable_paths=(*access.writable_paths, config_directory),
                    environment_names=access.environment_names, environment_overrides=access.environment_overrides,
                )
                if container:
                    prefix[1] = container_path(config_directory, is_windows=is_windows)
            command = [agent, *prefix, "--yolo", prompt_text]
        case "auggie":
            command = [agent, "--print", prompt_text]
        case "oz":
            from stackops.scripts.python.helpers.helpers_agents.mcp_install import resolve_oz_mcp_config_paths
            from stackops.utils.accessories import get_repo_root

            command = [agent, "agent", "run"]
            for path in resolve_oz_mcp_config_paths(repo_root=get_repo_root(Path.cwd()), home_dir=Path.home()):
                input_paths.append(path)
                command.extend(["--mcp", container_path(path, is_windows=is_windows) if container else str(path)])
            command.extend(["--prompt", prompt_text])
        case "droid":
            command = [agent, "exec", "-f", prompt_argument]
        case "cursor-agent":
            command = [agent, "-p", prompt_text, "--output-format", "text"]

    wrapped = build_sandbox_command(
        command=command, options=options, directory=Path.cwd(), access=access,
        read_only_paths=tuple(input_paths), interactive=False,
    )
    if is_windows:
        script = "& " + " ".join(quote_for_shell(argument, is_windows=True) for argument in wrapped)
    else:
        script = shlex.join(wrapped)
    if agent == "codex":
        prompt_path = quote_for_shell(str(prompt_file), is_windows=is_windows)
        script = f"""Get-Content -Raw {prompt_path} | {script}""" if is_windows else f"""{script} < {prompt_path}"""
    elif agent == "pi":
        monitor_command = [sys.executable, str(Path(__file__).with_name("agents_run_pi_monitor.py"))]
        if is_windows:
            monitor = "& " + " ".join(quote_for_shell(argument, is_windows=True) for argument in monitor_command)
            script = f"""& {{ {script}; $global:stackopsSandboxExitCode = $LASTEXITCODE }} | {monitor}
exit $global:stackopsSandboxExitCode"""
        else:
            script = f"""set -o pipefail; {script} | {shlex.join(monitor_command)}"""
    return script
