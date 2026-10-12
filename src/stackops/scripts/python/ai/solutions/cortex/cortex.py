import json
from pathlib import Path

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root / "AGENTS.md",
            content=get_generic_instructions_path().read_text(encoding="utf-8"),
            write_mode="if_missing",
        )
        if change is not None:
            changes.append(change)
    if add_private_config:
        configurations: tuple[tuple[str, dict[str, object]], ...] = (
            ("settings.json", {}),
            ("mcp.json", {"mcpServers": {}}),
        )
        for name, content in configurations:
            change = write_text_artifact(
                repo_root=repo_root,
                path=repo_root / ".cortex" / name,
                content=json.dumps(content, indent=2) + "\n",
                write_mode="if_missing",
            )
            if change is not None:
                changes.append(change)
    return tuple(changes)
