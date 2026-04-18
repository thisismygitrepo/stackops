from stackops.scripts.python.helpers.helpers_agents.privacy.configs.gemini import SETTINGS_PATH_REFERENCE


def test_settings_path_reference_matches_expected_filename() -> None:
    assert SETTINGS_PATH_REFERENCE == "settings.json"
