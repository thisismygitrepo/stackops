from stackops.scripts.python.helpers.helpers_agents import agents_parallel_run_impl


def test_should_scaffold_parallel_yaml_prefers_repo_for_default_all() -> None:
    assert agents_parallel_run_impl._should_scaffold_parallel_yaml(location_name="repo", parallel_yaml_path=None, where="all") is True
    assert agents_parallel_run_impl._should_scaffold_parallel_yaml(location_name="private", parallel_yaml_path=None, where="all") is False


def test_should_scaffold_parallel_yaml_only_creates_requested_non_repo_locations() -> None:
    assert agents_parallel_run_impl._should_scaffold_parallel_yaml(location_name="private", parallel_yaml_path=None, where="private") is True
    assert agents_parallel_run_impl._should_scaffold_parallel_yaml(location_name="public", parallel_yaml_path=None, where="public") is True
    assert agents_parallel_run_impl._should_scaffold_parallel_yaml(location_name="library", parallel_yaml_path=None, where="library") is False
    assert agents_parallel_run_impl._should_scaffold_parallel_yaml(location_name="repo", parallel_yaml_path="custom.yaml", where="all") is True
