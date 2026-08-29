import json
from pathlib import Path

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def _write_json_if_missing(*, repo_root: Path, path: Path, content: dict[str, object]) -> ArtifactChange | None:
    return write_text_artifact(
        repo_root=repo_root,
        path=path,
        content=json.dumps(content, indent=2) + "\n",
        write_mode="if_missing",
    )


def _write_text_if_missing(*, repo_root: Path, path: Path, content: str) -> ArtifactChange | None:
    return write_text_artifact(repo_root=repo_root, path=path, content=content, write_mode="if_missing")


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
        change = _write_text_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_text,
        )
        if change is not None:
            changes.append(change)

    if add_private_config:
        settings_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".pi/settings.json"),
            content={
                "defaultThinkingLevel": "max",
                "enableInstallTelemetry": False,
                "retry": {
                    "enabled": True,
                    "maxRetries": 10,
                    "baseDelayMs": 2_000,
                    "provider": {
                        "maxRetries": 0,
                        "maxRetryDelayMs": 60_000,
                    },
                },
            },
        )
        mcp_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".pi/mcp.json"),
            content={"mcpServers": {}},
        )
        changes.extend(change for change in (settings_change, mcp_change) if change is not None)
    return tuple(changes)
