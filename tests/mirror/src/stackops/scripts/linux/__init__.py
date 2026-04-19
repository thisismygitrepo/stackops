

from stackops.scripts import linux as linux_scripts
from stackops.utils.path_reference import get_path_reference_path


def test_wrap_stackops_reference_resolves_to_packaged_script() -> None:
    script_path = get_path_reference_path(module=linux_scripts, path_reference=linux_scripts.WRAP_STACKOPS_PATH_REFERENCE)

    assert script_path.is_file()
    assert script_path.name == linux_scripts.WRAP_STACKOPS_PATH_REFERENCE
    assert script_path.read_text(encoding="utf-8").strip() != ""
