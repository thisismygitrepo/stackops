import json
from pathlib import Path

import stackops.scripts.python.ai.solutions.kilocode as kilocode_assets
from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.solutions.opencode.openrouter_config import enforce_openrouter_zdr, read_openrouter_config
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
        config_paths = [
            path
            for directory in (repo_root, repo_root.joinpath(".kilo"))
            for name in ("kilo.json", "kilo.jsonc")
            if (path := directory.joinpath(name)).exists()
        ]
        if not config_paths:
            config_paths.append(repo_root.joinpath(".kilo/kilo.jsonc"))
        for config_path in config_paths:
            config = read_openrouter_config(config_path) if config_path.exists() else {}
            enforce_openrouter_zdr(config)
            config_change = write_text_artifact(
                repo_root=repo_root,
                path=config_path,
                content=json.dumps(config, indent=2) + "\n",
                write_mode="always",
            )
            assert config_change is not None
            changes.append(config_change)
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
