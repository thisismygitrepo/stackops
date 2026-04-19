

from pathlib import Path

from stackops.scripts.python.ai.solutions.droid.droid import build_configuration
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def test_build_configuration_writes_droid_markdown_when_enabled(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=True)

    assert tmp_path.joinpath("DROID.md").read_text(encoding="utf-8") == get_generic_instructions_path().read_text(encoding="utf-8")


def test_build_configuration_skips_output_when_instructions_disabled(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=False)

    assert not tmp_path.joinpath("DROID.md").exists()
