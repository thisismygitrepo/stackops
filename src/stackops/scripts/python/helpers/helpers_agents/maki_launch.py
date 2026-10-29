from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.agents_shell import quote_for_shell
from stackops.utils.schemas.fire_agents.fire_agents_types import PROVIDER


def build_maki_command(*, model: str | None, provider: PROVIDER | None) -> list[str]:
    if provider is not None:
        raise ValueError("Maki selects its provider through --model provider/model-id; a separate --provider is unsupported.")
    command = ["maki", "--yolo"]
    if model is not None:
        command.extend(["--model", model])
    return command


def render_maki_prompt_command(*, command: list[str], prompt_file: Path, is_windows: bool) -> str:
    prompt_path = quote_for_shell(str(prompt_file), is_windows=is_windows)
    if is_windows:
        invocation = "& " + " ".join(quote_for_shell(argument, is_windows=True) for argument in command)
        return f"""Get-Content -Raw -Encoding UTF8 {prompt_path} | {invocation} --print"""
    return f"""{shlex.join(command)} --print < {prompt_path}"""
