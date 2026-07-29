from pathlib import Path

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    _ = add_private_config
    if add_instructions is False:
        return ()
    instructions_path = get_generic_instructions_path()
    change = write_text_artifact(
        repo_root=repo_root,
        path=repo_root.joinpath(".clinerules/python_dev.md"),
        content=instructions_path.read_text(encoding="utf-8"),
        write_mode="always",
    )
    assert change is not None
    return (change,)
