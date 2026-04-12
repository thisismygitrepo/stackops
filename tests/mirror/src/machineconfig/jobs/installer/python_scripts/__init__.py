from __future__ import annotations

from pathlib import Path

from machineconfig.jobs.installer import python_scripts



def test_python_scripts_package_has_no_public_exports() -> None:
    package_file = Path(python_scripts.__file__).resolve()
    public_names = sorted(
        name for name in vars(python_scripts) if not name.startswith("__")
    )

    assert package_file.is_file()
    assert public_names == []
