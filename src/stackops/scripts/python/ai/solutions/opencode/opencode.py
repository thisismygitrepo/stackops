
from pathlib import Path

import stackops.scripts.python.ai.solutions.opencode as opencode_assets
from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
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
        opencode_config = repo_root.joinpath(".opencode/opencode.jsonc")
        library_config_path = get_path_reference_path(
            module=opencode_assets,
            path_reference=opencode_assets.OPENCODE_PATH_REFERENCE,
        )
        change = write_text_artifact(
            repo_root=repo_root,
            path=opencode_config,
            content=library_config_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)
    return tuple(changes)
