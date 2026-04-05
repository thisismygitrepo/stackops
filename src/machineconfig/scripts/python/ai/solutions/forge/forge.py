import json
from pathlib import Path

from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


FORGE_SCHEMA_URL = "https://raw.githubusercontent.com/antinomyhq/forge/main/forge.schema.json"


def _write_text_if_missing(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data=content, encoding="utf-8")


def _write_json_if_missing(path: Path, content: dict[str, object]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data=json.dumps(content, indent=2) + "\n", encoding="utf-8")


def _default_forge_yaml() -> str:
    return f"""# yaml-language-server: $schema={FORGE_SCHEMA_URL}
"""


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> None:
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        repo_root.joinpath("AGENTS.md").write_text(data=instructions_path.read_text(encoding="utf-8"), encoding="utf-8")

    if add_private_config:
        _write_text_if_missing(path=repo_root.joinpath("forge.yaml"), content=_default_forge_yaml())
        _write_json_if_missing(path=repo_root.joinpath(".mcp.json"), content={"mcpServers": {}})
