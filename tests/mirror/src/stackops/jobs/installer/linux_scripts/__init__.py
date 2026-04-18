from __future__ import annotations

from pathlib import Path

from stackops.jobs.installer import linux_scripts
from stackops.utils.path_reference import get_path_reference_path


def _path_reference_names() -> tuple[str, ...]:
    return tuple(sorted(name for name, value in vars(linux_scripts).items() if name.endswith("_PATH_REFERENCE") and isinstance(value, str)))


def test_all_linux_script_path_references_resolve_to_files() -> None:
    module_dir = Path(linux_scripts.__file__).resolve().parent
    reference_names = _path_reference_names()

    assert reference_names
    for reference_name in reference_names:
        relative_name = getattr(linux_scripts, reference_name)
        resolved_path = get_path_reference_path(module=linux_scripts, path_reference=relative_name)

        assert resolved_path.parent == module_dir
        assert resolved_path.is_file()
        assert resolved_path.name == relative_name


def test_linux_path_references_cover_all_shell_scripts() -> None:
    module_dir = Path(linux_scripts.__file__).resolve().parent
    referenced_files = {getattr(linux_scripts, reference_name) for reference_name in _path_reference_names()}
    actual_files = {path.name for path in module_dir.glob("*.sh")}

    assert referenced_files == actual_files
