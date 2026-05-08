from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC
from stackops.scripts.python.helpers.helpers_agents.reasoning_capabilities import copilot_reasoning_args


def fire_copilot(ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    prompt_rel = prompt_path.relative_to(repo_root)
    safe_prompt_path = shlex.quote(str(prompt_rel))
    model_value = ai_spec["model"]
    reasoning_effort = ai_spec["reasoning_effort"]
    command_parts: list[str] = ["copilot", "-p", f'"$(cat {safe_prompt_path})"']
    if model_value is not None:
        command_parts.extend(["--model", shlex.quote(model_value)])
    copilot_reasoning = copilot_reasoning_args(reasoning_effort=reasoning_effort)
    if len(copilot_reasoning) > 0:
        command_parts.extend([copilot_reasoning[0], shlex.quote(copilot_reasoning[1])])
    command_parts.append("--yolo")
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
