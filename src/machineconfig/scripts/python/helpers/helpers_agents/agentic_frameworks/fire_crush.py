
from pathlib import Path
# import shlex
import machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks as framework_assets
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC
from machineconfig.utils.path_reference import get_path_reference_path


def fire_crush(ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    if ai_spec["machine"] == "local":
        return f"""
crush run {prompt_path}
"""
    assert ai_spec["api_spec"]["api_key"] is not None, "API key is required for Crush agent in docker mode."
    json_path = get_path_reference_path(
        module=framework_assets,
        path_reference=framework_assets.FIRE_CRUSH_PATH_REFERENCE,
    )
    json_template = json_path.read_text(encoding="utf-8")
    api_key = ai_spec["api_spec"]["api_key"]
    json_filled = json_template.replace("{api_key}", api_key)
    if ai_spec["model"] is not None:
        json_filled = json_filled.replace("{model}", ai_spec["model"])
    provider: str | None = "gemini" if ai_spec["provider"] == "google" else ai_spec["provider"]
    if provider is None:
        raise ValueError("Provider must be specified for Crush agent.")
    json_filled = json_filled.replace("{provider}", provider)
    from machineconfig.utils.accessories import randstr
    temp_config_file_local = Path.home().joinpath("tmp_results/tmp_files/crush_" + randstr(8) + ".json")
    temp_config_file_local.parent.mkdir(parents=True, exist_ok=True)
    Path(temp_config_file_local).write_text(json_filled, encoding="utf-8")
    return f"""

docker run -it --rm \
  -v "{repo_root}:/workspace/{repo_root.name}" \
  -v "{temp_config_file_local}:/root/.local/share/crush/crush.json" \
  -w "/workspace/{repo_root.name}" \
  statistician/machineconfig-ai:latest \
  bash -i -c "source ~/.bashrc && cd /workspace/{repo_root.name} && cat /root/.local/share/crush/crush.json && crush run 'Please act on contents of this prompt ./{prompt_path.relative_to(repo_root)}'"

"""
