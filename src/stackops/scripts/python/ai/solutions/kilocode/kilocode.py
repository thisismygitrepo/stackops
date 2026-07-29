import json
from pathlib import Path

import stackops.scripts.python.ai.solutions.kilocode as kilocode_assets
from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path
from stackops.utils.path_reference import get_path_reference_path


def _write_json_if_missing(*, repo_root: Path, path: Path, content: dict[str, object]) -> ArtifactChange | None:
    return write_text_artifact(
        repo_root=repo_root,
        path=path,
        content=json.dumps(content, indent=2) + "\n",
        write_mode="if_missing",
    )


def _write_text_if_missing(*, repo_root: Path, path: Path, content: str) -> ArtifactChange | None:
    return write_text_artifact(repo_root=repo_root, path=path, content=content, write_mode="if_missing")


def _default_kilocodeignore() -> str:
    return (
        "# Secrets and credentials\n"
        ".env\n"
        ".env.*\n"
        "secrets/\n"
        "**/*.pem\n"
        "**/*.key\n"
        "**/credentials*.json\n"
        "!*.env.example\n"
    )


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    kilo_rules_dir = repo_root.joinpath(".kilocode/rules")

    if add_instructions:
        instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
        rules_change = write_text_artifact(
            repo_root=repo_root,
            path=kilo_rules_dir.joinpath("rules.md"),
            content=instructions_text,
            write_mode="always",
        )
        agents_change = _write_text_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_text,
        )
        assert rules_change is not None
        changes.append(rules_change)
        if agents_change is not None:
            changes.append(agents_change)

    if add_private_config:
        mcp_change = _write_json_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".kilocode/mcp.json"),
            content={"mcpServers": {}},
        )
        ignore_change = _write_text_if_missing(
            repo_root=repo_root,
            path=repo_root.joinpath(".kilocodeignore"),
            content=_default_kilocodeignore(),
        )
        privacy_source = get_path_reference_path(
            module=kilocode_assets,
            path_reference=kilocode_assets.PRIVACY_PATH_REFERENCE,
        )
        privacy_change = _write_text_if_missing(
            repo_root=repo_root,
            path=kilo_rules_dir.joinpath("privacy.md"),
            content=privacy_source.read_text(encoding="utf-8"),
        )
        changes.extend(change for change in (mcp_change, ignore_change, privacy_change) if change is not None)
    return tuple(changes)
