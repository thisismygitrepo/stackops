

from pathlib import Path

from stackops.jobs.installer import powershell_scripts
from stackops.utils.path_reference import get_path_reference_path


def _path_reference_names() -> tuple[str, ...]:
    return tuple(sorted(name for name, value in vars(powershell_scripts).items() if name.endswith("_PATH_REFERENCE") and isinstance(value, str)))


def test_all_powershell_path_references_resolve_to_files() -> None:
    module_dir = Path(powershell_scripts.__file__).resolve().parent
    reference_names = _path_reference_names()

    assert reference_names
    for reference_name in reference_names:
        relative_name = getattr(powershell_scripts, reference_name)
        resolved_path = get_path_reference_path(module=powershell_scripts, path_reference=relative_name)

        assert resolved_path.parent == module_dir
        assert resolved_path.is_file()
        assert resolved_path.name == relative_name


def test_powershell_path_references_cover_all_ps1_scripts() -> None:
    module_dir = Path(powershell_scripts.__file__).resolve().parent
    referenced_files = {getattr(powershell_scripts, reference_name) for reference_name in _path_reference_names()}
    actual_files = {path.name for path in module_dir.glob("*.ps1")}

    assert referenced_files == actual_files
