

"""
ref: https://github.com/charmbracelet/crush

"""

from pathlib import Path
import platform

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path



def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("CRUSH.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)

    if add_private_config:
        repo_settings = repo_root.joinpath(".crush.json")
        ignore_settings = repo_root.joinpath(".crushignore")
        if platform.system() == "Windows":
            global_settings = Path.home().joinpath("AppData/Local/crush/crush.json")
        else:
            global_settings = Path.home().joinpath(".config/crush/crush.json")

        _ = repo_settings, ignore_settings, global_settings  # to avoid unused variable warnings
    return tuple(changes)
