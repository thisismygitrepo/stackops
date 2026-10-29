import re

import stackops.scripts.setup.linux as linux_setup_assets
import stackops.scripts.setup.windows as windows_setup_assets
from stackops.utils.constants import STACKOPS_PYTHON_VERSION
from stackops.utils.path_reference import get_path_reference_path
from stackops.utils.source_of_truth import REPO_ROOT


def test_non_python_files_pin_stackops_python_version() -> None:
    pinned_files = [
        get_path_reference_path(module=linux_setup_assets, path_reference=linux_setup_assets.QUICK_INIT_PATH_REFERENCE),
        get_path_reference_path(module=linux_setup_assets, path_reference=linux_setup_assets.INTERACTIVE_PATH_REFERENCE),
        get_path_reference_path(module=windows_setup_assets, path_reference=windows_setup_assets.QUICK_INIT_PATH_REFERENCE),
        REPO_ROOT.joinpath("jobs", "dockers", "Dockerfile_slim"),
        REPO_ROOT.joinpath(".github", "workflows", "docs.yml"),
        REPO_ROOT.joinpath(".github", "workflows", "publish-to-pypi.yml"),
    ]
    version_pattern = re.compile(r"""(?:--python |python-version: ')(\d+\.\d+)""")
    pinned_versions = {str(path): set(version_pattern.findall(path.read_text(encoding="utf-8"))) for path in pinned_files}

    assert {path: versions for path, versions in pinned_versions.items() if versions != {STACKOPS_PYTHON_VERSION}} == {}, (
        f"""Pin Python {STACKOPS_PYTHON_VERSION} (STACKOPS_PYTHON_VERSION) in these files: {pinned_versions}"""
    )
