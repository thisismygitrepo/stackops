import json
from pathlib import Path

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


FORGE_SCHEMA_URL = "https://raw.githubusercontent.com/antinomyhq/forge/main/forge.schema.json"


def _write_text_if_missing(*, repo_root: Path, path: Path, content: str) -> ArtifactChange | None:
    return write_text_artifact(repo_root=repo_root, path=path, content=content, write_mode="if_missing")


def _write_json_if_missing(*, repo_root: Path, path: Path, content: dict[str, object]) -> ArtifactChange | None:
    return write_text_artifact(
        repo_root=repo_root,
        path=path,
        content=json.dumps(content, indent=2) + "\n",
        write_mode="if_missing",
    )


def _default_forge_yaml() -> str:
    return f"""# yaml-language-server: $schema={FORGE_SCHEMA_URL}
"""


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)

    if add_private_config:
        forge_change = _write_text_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath("forge.yaml"),
            content=_default_forge_yaml(),
        )
        mcp_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".mcp.json"),
            content={"mcpServers": {}},
        )
        changes.extend(change for change in (forge_change, mcp_change) if change is not None)
    return tuple(changes)
