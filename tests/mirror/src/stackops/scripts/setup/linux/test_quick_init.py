import pytest

import stackops.scripts.setup.linux as linux_setup_assets
from stackops.profile.shell_profile_source import build_shell_profile_source
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.source_of_truth import CONFIG_ROOT


@pytest.mark.parametrize("shell_variable", ["/bin/bash", "/bin/zsh"])
def test_quick_init_ends_by_sourcing_the_init_installed_into_the_shell_profile(shell_variable: str) -> None:
    quick_init_path = get_path_reference_path(module=linux_setup_assets, path_reference=linux_setup_assets.QUICK_INIT_PATH_REFERENCE)
    profile_source = build_shell_profile_source(system_name="Linux", shell_variable=shell_variable, config_root=CONFIG_ROOT)

    assert quick_init_path.read_text(encoding="utf-8").splitlines()[-1] == profile_source.source_line
