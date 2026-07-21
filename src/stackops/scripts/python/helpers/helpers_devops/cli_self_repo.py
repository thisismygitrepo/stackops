from pathlib import Path

from stackops.utils.source_of_truth import STACKOPS_REPO_DIR


def developer_repo_root() -> Path | None:
    if STACKOPS_REPO_DIR.joinpath("pyproject.toml").is_file():
        return STACKOPS_REPO_DIR
    return None
