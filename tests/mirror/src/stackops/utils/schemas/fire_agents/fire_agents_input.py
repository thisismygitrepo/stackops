

from typing import get_args

from stackops.utils.schemas.fire_agents import fire_agents_input as fire_agents_input_module


def test_search_strategies_literal_options_match_supported_modes() -> None:
    assert get_args(fire_agents_input_module.SEARCH_STRATEGIES) == ("file_path", "keyword_search", "filename_pattern")


def test_file_path_search_input_requires_both_runtime_keys() -> None:
    assert fire_agents_input_module.FilePathSearchInput.__required_keys__ == frozenset({"file_path", "separator"})
    assert fire_agents_input_module.FilePathSearchInput.__optional_keys__ == frozenset()


def test_fire_agents_main_input_marks_strategy_specific_keys_optional() -> None:
    assert fire_agents_input_module.FireAgentsMainInput.__optional_keys__ == frozenset(
        {"file_path_input", "keyword_search_input", "filename_pattern_input"}
    )
    assert fire_agents_input_module.FireAgentsMainInput.__required_keys__ == frozenset(
        {
            "repo_root",
            "search_strategy",
            "agent_selected",
            "prompt_prefix",
            "job_name",
            "keep_material_in_separate_file",
            "max_agents",
            "tasks_per_prompt",
        }
    )


def test_fire_agents_runtime_data_requires_all_runtime_fields() -> None:
    assert fire_agents_input_module.FireAgentsRuntimeData.__required_keys__ == frozenset(
        {"prompt_material", "separator", "prompt_material_re_splitted", "random_name"}
    )
