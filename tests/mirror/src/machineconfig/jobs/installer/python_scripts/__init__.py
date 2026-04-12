from __future__ import annotations

from machineconfig.utils.source_of_truth import REPO_ROOT



def test_python_scripts_package_init_file_is_empty() -> None:
    package_file = REPO_ROOT / "src" / "machineconfig" / "jobs" / "installer" / "python_scripts" / "__init__.py"

    assert package_file.is_file()
    assert package_file.read_text(encoding="utf-8").strip() == ""
