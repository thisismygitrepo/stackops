

from pathlib import Path

import stackops.scripts.python.ai.solutions.codex as codex_package


def test_codex_package_references_existing_private_config_template() -> None:
    assert codex_package.__file__ is not None
    module_path = Path(codex_package.__file__)
    referenced_path = module_path.with_name(codex_package.CONFIG_PATH_REFERENCE)

    assert referenced_path.is_file()
    assert referenced_path.read_text(encoding="utf-8") != ""
