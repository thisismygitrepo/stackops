from pathlib import Path
import shlex

from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC


def fire_copilot(ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    prompt_rel = prompt_path.relative_to(repo_root)
    safe_prompt_path = shlex.quote(str(prompt_rel))
    model_value = ai_spec["model"]
    model_arg = f"--model {shlex.quote(model_value)}" if model_value else ""
    reasoning_effort = ai_spec["reasoning_effort"]
    reasoning_arg = f"--reasoning {shlex.quote(reasoning_effort)}" if reasoning_effort else ""
    base_cmd = f"""copilot -p "$(cat {safe_prompt_path})" {model_arg} {reasoning_arg} --yolo """
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
