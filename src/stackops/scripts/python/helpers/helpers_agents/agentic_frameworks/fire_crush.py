import json
import shlex
from pathlib import Path

import stackops.scripts.python.helpers.helpers_agents.agentic_frameworks as framework_assets
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.schemas.fire_agents.fire_agents_types import AI_SPEC


CRUSH_API_KEY_ENV = "STACKOPS_CRUSH_API_KEY"
CRUSH_CONFIG_PATH = Path("/root/.local/share/crush/crush.json")


def fire_crush(ai_spec: AI_SPEC, prompt_path: Path, repo_root: Path) -> str:
    if ai_spec["machine"] == "local":
        return f"""
crush run {prompt_path}
"""
    provider = ai_spec["provider"]
    if provider is None:
        raise ValueError("Provider must be specified for Crush agent.")
    json_path = get_path_reference_path(
        module=framework_assets,
        path_reference=framework_assets.FIRE_CRUSH_PATH_REFERENCE,
    )
    json_template = json_path.read_text(encoding="utf-8")
    json_filled = json_template.replace('"{provider}"', json.dumps(provider))
    if ai_spec["model"] is not None:
        json_filled = json_filled.replace('"{model}"', json.dumps(ai_spec["model"]))
    config_writer = f"""import json
import os
from pathlib import Path

api_key = os.environ[{CRUSH_API_KEY_ENV!r}]
if not api_key:
    raise RuntimeError("Crush API key is empty.")
config_json = {json_filled!r}.replace('"{{api_key}}"', json.dumps(api_key))
config_path = Path({CRUSH_CONFIG_PATH.as_posix()!r})
config_path.parent.mkdir(parents=True, exist_ok=True)
config_path.write_text(config_json, encoding="utf-8")
config_path.chmod(0o600)
"""
    container_workspace = f"/workspace/{repo_root.name}"
    prompt = f"Please act on contents of this prompt ./{prompt_path.relative_to(repo_root)}"
    container_command = " && ".join(
        (
            "source ~/.bashrc",
            "umask 077",
            f"python -c {shlex.quote(config_writer)}",
            f"unset {CRUSH_API_KEY_ENV}",
            f"cd {shlex.quote(container_workspace)}",
            f"crush run {shlex.quote(prompt)}",
        )
    )
    return f"""

docker run -it --rm \
  -e {CRUSH_API_KEY_ENV} \
  -v "{repo_root}:/workspace/{repo_root.name}" \
  -w "{container_workspace}" \
  statistician/stackops-ai:latest \
  bash -i -c {shlex.quote(container_command)}

"""
