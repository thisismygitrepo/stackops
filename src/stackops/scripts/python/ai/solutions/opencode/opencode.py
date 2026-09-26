import json
from pathlib import Path

import stackops.scripts.python.ai.solutions.opencode as opencode_assets
from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.solutions.opencode.openrouter_config import enforce_openrouter_zdr, read_openrouter_config
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path
from stackops.utils.path_reference import get_path_reference_path


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        instructions_text = instructions_path.read_text(encoding="utf-8")

        # opencode_instructions_dir = repo_root.joinpath(".github/instructions")
        # opencode_instructions_dir.mkdir(parents=True, exist_ok=True)
        # opencode_rules_path = opencode_instructions_dir.joinpath("opencode_rules.md")
        # opencode_rules_path.write_text(data=instructions_text, encoding="utf-8")

        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_text,
            write_mode="if_missing",
        )
        if change is not None:
            changes.append(change)

    if add_private_config:
        library_config_path = get_path_reference_path(
            module=opencode_assets,
            path_reference=opencode_assets.OPENCODE_PATH_REFERENCE,
        )
        config_paths = [
            path
            for directory in (repo_root, repo_root.joinpath(".opencode"))
            for name in ("opencode.json", "opencode.jsonc")
            if (path := directory.joinpath(name)).exists()
        ]
        if not config_paths:
            config_paths.append(repo_root.joinpath(".opencode/opencode.jsonc"))
        for config_path in config_paths:
            source_path = config_path if config_path.exists() else library_config_path
            config = read_openrouter_config(source_path)
            enforce_openrouter_zdr(config)
            change = write_text_artifact(
                repo_root=repo_root,
                path=config_path,
                content=json.dumps(config, indent=2) + "\n",
                write_mode="always",
            )
            assert change is not None
            changes.append(change)
    return tuple(changes)
