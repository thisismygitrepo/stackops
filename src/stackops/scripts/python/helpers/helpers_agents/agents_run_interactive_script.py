import shlex
from pathlib import Path
from platform import system

from stackops.scripts.python.helpers.helpers_agents.agents_run_interactive import build_interactive_prompt_command
from stackops.scripts.python.helpers.helpers_agents.agents_run_sandbox import validate_prompt_sandbox
from stackops.scripts.python.helpers.helpers_agents.agents_sandbox import resolve_sandbox_access
from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort
from stackops.utils.sandbox.launch import build_sandbox_command
from stackops.utils.sandbox.options import SandboxBackend, SandboxOptions
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


def build_interactive_prompt_script(
    *,
    agent: AGENTS,
    prompt_file: Path,
    reasoning_effort: ReasoningEffort | None,
    options: SandboxOptions,
) -> str:
    validate_prompt_sandbox(agent=agent, options=options)
    command = build_interactive_prompt_command(
        agent=agent,
        prompt=prompt_file.read_text(encoding="utf-8"),
        reasoning_effort=reasoning_effort,
        external_sandbox=options.backend != SandboxBackend.NONE,
    )
    if options.backend != SandboxBackend.NONE:
        command = build_sandbox_command(
            command=command,
            options=options,
            directory=Path.cwd(),
            access=resolve_sandbox_access(agent=agent),
            read_only_paths=(),
            interactive=True,
        )
    if system() == "Windows":
        return "& " + " ".join(quote_for_shell(argument, is_windows=True) for argument in command)
    return shlex.join(command)
