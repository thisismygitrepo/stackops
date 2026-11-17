from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.utils.schemas.fire_agents.fire_agents_types import PROVIDER, ReasoningEffort


def build_prime_agent_command(*, model: str | None, provider: PROVIDER | None, reasoning_effort: ReasoningEffort | None) -> list[str]:
    command = ["prime-agent"]
    if provider is not None:
        command.extend(["--provider", provider])
    if model is not None:
        command.extend(["--model", model])
    if reasoning_effort is not None:
        command.extend(["--thinking", "off" if reasoning_effort == "none" else reasoning_effort])
    return command


def render_prime_agent_prompt_command(*, command: list[str], prompt_file: Path, is_windows: bool) -> str:
    prompt_path = quote_for_shell(str(prompt_file), is_windows=is_windows)
    if is_windows:
        invocation = "& " + " ".join(quote_for_shell(argument, is_windows=True) for argument in command)
        return f"""Get-Content -Raw -Encoding UTF8 {prompt_path} | {invocation} --print"""
    return f"""{shlex.join(command)} --print < {prompt_path}"""
