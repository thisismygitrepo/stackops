from pathlib import Path

import stackops.scripts.python.ai.solutions.gemini as gemini_assets
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path
from stackops.utils.path_reference import get_path_reference_path


def _build_gemini_instructions_text() -> str:
    generic_instructions_path = get_generic_instructions_path()
    gemini_instructions_path = get_path_reference_path(
        module=gemini_assets,
        path_reference=gemini_assets.INSTRUCTIONS_PATH_REFERENCE,
    )
    generic_instructions = generic_instructions_path.read_text(encoding="utf-8").rstrip()
    gemini_instructions = gemini_instructions_path.read_text(encoding="utf-8").rstrip()
    return f"{generic_instructions}\n\n{gemini_instructions}\n"


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> None:
    if add_instructions:
        repo_root.joinpath("GEMINI.md").write_text(data=_build_gemini_instructions_text(), encoding="utf-8")

    if add_private_config:
        gemini_dir = repo_root.joinpath(".gemini")
        settings_source_path = get_path_reference_path(
            module=gemini_assets,
            path_reference=gemini_assets.SETTINGS_PATH_REFERENCE,
        )
        gemini_dir.mkdir(parents=True, exist_ok=True)
        gemini_dir.joinpath("settings.json").write_text(data=settings_source_path.read_text(encoding="utf-8"), encoding="utf-8")
