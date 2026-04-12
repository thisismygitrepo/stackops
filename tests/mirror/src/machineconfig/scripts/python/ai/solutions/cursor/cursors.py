from __future__ import annotations

from pathlib import Path

from machineconfig.scripts.python.ai.solutions.cursor.cursors import build_configuration
from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


def test_build_configuration_writes_cursor_rules_when_enabled(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=True)

    cursor_rules_path = tmp_path.joinpath(".cursor", "rules", "python_dev.mdc")

    assert cursor_rules_path.is_file()
    assert cursor_rules_path.read_text(encoding="utf-8") == get_generic_instructions_path().read_text(encoding="utf-8")


def test_build_configuration_skips_cursor_rules_when_instructions_disabled(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=False)

    assert not tmp_path.joinpath(".cursor").exists()
