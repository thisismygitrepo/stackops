from typing import assert_never

from stackops.scripts.python.helpers.helpers_agents.constants import CODEX_WORKSPACE_PERMISSION_ARGS
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import (
    ReasoningEffort,
    copilot_reasoning_args,
    normalize_reasoning_effort,
)
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


def build_interactive_prompt_command(
    *,
    agent: AGENTS,
    prompt: str,
    reasoning_effort: ReasoningEffort | None,
    external_sandbox: bool,
) -> list[str]:
    reasoning = normalize_reasoning_effort(agent=agent, reasoning_effort=reasoning_effort)
    command: list[str] = [agent]
    match agent:
        case "codex":
            if external_sandbox:
                command.append("--dangerously-bypass-approvals-and-sandbox")
            else:
                command.extend(CODEX_WORKSPACE_PERMISSION_ARGS)
            if reasoning is not None:
                command.extend(["-c", f'''model_reasoning_effort="{reasoning}"'''])
            command.extend(["--", prompt])
        case "copilot":
            command.extend([*copilot_reasoning_args(reasoning_effort=reasoning), "--yolo", "--interactive", prompt])
        case "pi":
            if reasoning is not None:
                command.extend(["--thinking", "off" if reasoning == "none" else reasoning])
            command.extend(["--", prompt])
        case "opencode":
            command.extend(["--prompt", prompt])
        case "agy":
            command.extend(["--dangerously-skip-permissions", "--prompt-interactive", prompt])
        case "qwen":
            command.extend(["--yolo", "--prompt-interactive", prompt])
        case "claude" | "cursor-agent" | "auggie" | "droid":
            command.extend(["--", prompt])
        case "deepseek":
            raise ValueError(
                "DeepSeek's web interface does not accept an initial CLI prompt. "
                "Use agents i -a deepseek and enter the prompt in the web session, or omit --interactive."
            )
        case "forge" | "crush" | "q" | "kilocode" | "cline" | "oz":
            raise ValueError(
                f"""--interactive is not supported for agent '{agent}'. """
                "Choose codex, copilot, pi, opencode, agy, qwen, claude, cursor-agent, auggie, or droid, or omit --interactive."
            )
        case _:
            assert_never(agent)
    return command


def validate_interactive_prompt_agent(*, agent: AGENTS) -> None:
    _ = build_interactive_prompt_command(
        agent=agent,
        prompt="",
        reasoning_effort=None,
        external_sandbox=False,
    )
