

import json
from pathlib import Path

import stackops.utils.installer_utils as installer_utils


def test_github_releases_reference_points_to_existing_json_file() -> None:
    package_dir = Path(installer_utils.__file__).resolve().parent
    releases_path = package_dir.joinpath(installer_utils.GITHUB_RELEASES_PATH_REFERENCE)
    payload: object = json.loads(releases_path.read_text(encoding="utf-8"))

    assert releases_path.is_file()
    assert isinstance(payload, (dict, list))
