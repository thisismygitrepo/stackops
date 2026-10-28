from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import normalize_reasoning_effort
from stackops.utils.repos.project import resolve_project_root
from stackops.utils.schemas.fire_agents.fire_agents_types import PROVIDER, ReasoningEffort


def build_cortex_command(
    *, model: str | None, provider: PROVIDER | None, reasoning_effort: ReasoningEffort | None,
    directory: Path,
) -> list[str]:
    from stackops.scripts.python.helpers.helpers_agents.mcp_install import resolve_agent_launch_prefix

    if provider is not None:
        raise ValueError("Cortex uses its configured Snowflake connection; --provider is unsupported.")
    command = ["cortex", "--bypass", *resolve_agent_launch_prefix(agent="cortex", repo_root=resolve_project_root(current_dir=directory))]
    if model is not None:
        command.extend(["--model", model])
    reasoning = normalize_reasoning_effort(agent="cortex", reasoning_effort=reasoning_effort)
    if reasoning is not None:
        command.extend(["--effort", "max" if reasoning == "xhigh" else reasoning])
    return command


def render_cortex_prompt_command(*, command: list[str], prompt_file: Path, is_windows: bool) -> str:
    prompt_path = quote_for_shell(str(prompt_file), is_windows=is_windows)
    if is_windows:
        invocation = "& " + " ".join(quote_for_shell(argument, is_windows=True) for argument in command)
        # On Windows, cortex -p only reads the first line of a multi-line argument (and rejects stdin),
        # so we flatten newlines to spaces. Design choice: markdown layout is lost, but every word reaches the model.
        return f"""{invocation} -p ((Get-Content -Raw {prompt_path}) -replace "`r?`n", ' ')"""
    return f'''{shlex.join(command)} -p "$(cat {prompt_path})"'''
