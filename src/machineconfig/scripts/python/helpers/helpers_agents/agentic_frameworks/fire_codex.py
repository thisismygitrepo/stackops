from pathlib import Path
import shlex

from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC


def fire_codex(ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    prompt_rel = prompt_path.relative_to(repo_root)
    safe_prompt_path = shlex.quote(str(prompt_rel))
    model_value = ai_spec["model"]
    reasoning_effort = ai_spec["reasoning_effort"]
    command_parts: list[str] = ["codex", "exec"]
    if model_value is not None:
        command_parts.extend(["--model", shlex.quote(model_value)])
    if reasoning_effort is not None:
        command_parts.extend(["-c", shlex.quote(f'model_reasoning_effort="{reasoning_effort}"')])
    command_parts.extend(["-", "<", safe_prompt_path])
    base_cmd = " ".join(command_parts)

    api_key = ai_spec["api_spec"]["api_key"]
    if api_key is not None:
        api_key_env = f'export CODEX_API_KEY="{shlex.quote(api_key)}"'
        local_cmd = f"{api_key_env}\n{base_cmd}"
    else:
        local_cmd = f'echo "Warning: No CODEX_API_KEY provided, hoping it is set in the environment."\n{base_cmd}'

    if ai_spec["machine"] == "local":
        return f"""
{local_cmd}
"""
    env_flag = f"-e CODEX_API_KEY={shlex.quote(api_key)}" if api_key is not None else ""
    safe_cmd = shlex.quote(base_cmd)
    return f"""
docker run -it --rm \
  {env_flag} \
  -v "{repo_root}:/workspace/{repo_root.name}" \
  -w "/workspace/{repo_root.name}" \
  statistician/machineconfig-ai:latest \
  bash -lc {safe_cmd}
"""
