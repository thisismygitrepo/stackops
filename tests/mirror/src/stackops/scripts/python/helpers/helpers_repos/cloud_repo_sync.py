import inspect

from stackops.scripts.python.helpers.helpers_repos import cloud_repo_sync


def test_main_defaults_repo_to_current_working_directory() -> None:
    repo_parameter = inspect.signature(cloud_repo_sync.main).parameters["repo"]

    assert repo_parameter.default == "."
