import json
from pathlib import Path

from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def _write_json_if_missing(path: Path, content: dict[str, object]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data=json.dumps(content, indent=2) + "\n", encoding="utf-8")


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> None:
    if add_instructions:
        instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
        repo_root.joinpath("AGENTS.md").write_text(data=instructions_text, encoding="utf-8")

    if add_private_config:
        _write_json_if_missing(path=repo_root.joinpath(".agents/mcp_config.json"), content={"mcpServers": {}})
