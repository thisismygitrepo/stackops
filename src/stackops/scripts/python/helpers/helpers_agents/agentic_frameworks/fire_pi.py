from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, ReasoningEffort


def _pi_thinking_level(reasoning_effort: ReasoningEffort | None) -> str | None:
    if reasoning_effort is None:
        return None
    if reasoning_effort == "none":
        return "off"
    return reasoning_effort


def fire_pi(ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    prompt_rel = prompt_path.relative_to(repo_root)
    safe_prompt_path = shlex.quote(str(prompt_rel))
    command_parts: list[str] = ["pi"]
    provider = ai_spec["provider"]
    model = ai_spec["model"]
    thinking_level = _pi_thinking_level(reasoning_effort=ai_spec["reasoning_effort"])
    if provider is not None:
        command_parts.extend(["--provider", shlex.quote(provider)])
    if model is not None:
        command_parts.extend(["--model", shlex.quote(model)])
    if thinking_level is not None:
        command_parts.extend(["--thinking", shlex.quote(thinking_level)])
    prompt_expr = f'"$(cat {safe_prompt_path})"'
    command_parts.extend(["-p", prompt_expr])
    base_cmd = " ".join(command_parts)

    if ai_spec["machine"] == "local":
        return f"""
{base_cmd}
"""

    safe_cmd = shlex.quote(base_cmd)
    return f"""
docker run -it --rm \
  -v "{repo_root}:/workspace/{repo_root.name}" \
  -w "/workspace/{repo_root.name}" \
  statistician/stackops-ai:latest \
  bash -lc {safe_cmd}
"""
