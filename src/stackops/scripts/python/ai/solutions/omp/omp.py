from pathlib import Path
from typing import Final

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


DEFAULT_OMP_CONFIG: Final[str] = """retry:
  enabled: true
  maxRetries: 10
  baseDelayMs: 500
  maxDelayMs: 300000
"""


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_text,
            write_mode="if_missing",
        )
        if change is not None:
            changes.append(change)

    if add_private_config:
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath(".omp/config.yml"),
            content=DEFAULT_OMP_CONFIG,
            write_mode="if_missing",
        )
        if change is not None:
            changes.append(change)
    return tuple(changes)
