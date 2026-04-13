from pathlib import Path

import pytest

import machineconfig.scripts.python.ai.scripts.paths as ai_script_paths
import machineconfig.scripts.python.ai.utils.generic as generic_module
import machineconfig.utils.source_of_truth as source_of_truth_module


def test_create_dot_scripts_copies_core_scripts_into_repo_root_type_checking_dir(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    target_dir = repo_root.joinpath(ai_script_paths.TYPE_CHECKING_SCRIPTS_DIRECTORY)
    stale_file = target_dir.joinpath("stale.py")
    target_dir.mkdir(parents=True)
    stale_file.write_text("stale", encoding="utf-8")

    generic_module.create_dot_scripts(repo_root=repo_root)

    source_dir = generic_module.LIBRARY_ROOT.joinpath("scripts/python/ai/scripts")
    assert stale_file.exists() is False
    assert target_dir == repo_root.joinpath("scripts", "type_checking")

    for script_name in ai_script_paths.TYPE_CHECKING_SCRIPT_PATH_REFERENCES:
        assert target_dir.joinpath(script_name).read_text(encoding="utf-8") == source_dir.joinpath(script_name).read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("platform_name", "input_text", "expected_text"),
    [
        ("Windows", "bash ./tool.sh", "PowerShell .\\tool.ps1"),
        ("Linux", "PowerShell .\\tool.ps1", "bash ./tool.sh"),
    ],
)
def test_adjust_for_os_translates_text_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform_name: str,
    input_text: str,
    expected_text: str,
) -> None:
    config_path = tmp_path.joinpath("config.md")
    config_path.write_text(input_text, encoding="utf-8")

    monkeypatch.setattr(generic_module.platform, "system", lambda: platform_name)

    assert generic_module.adjust_for_os(config_path=config_path) == expected_text


def test_adjust_for_os_leaves_non_text_files_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path.joinpath("config.json")
    config_path.write_text('{"shell": "bash"}', encoding="utf-8")

    monkeypatch.setattr(generic_module.platform, "system", lambda: "Plan9")

    assert generic_module.adjust_for_os(config_path=config_path) == '{"shell": "bash"}'


def test_adjust_gitignore_appends_unique_default_and_extra_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gitignore_path = tmp_path.joinpath(".gitignore")
    gitignore_path.write_text("node_modules", encoding="utf-8")

    monkeypatch.setattr(source_of_truth_module, "EXCLUDE_DIRS", ["build", "node_modules"])

    generic_module.adjust_gitignore(repo_root=tmp_path, include_default_entries=True, extra_entries=["custom", " build ", ""])

    assert gitignore_path.read_text(encoding="utf-8") == "node_modules\nbuild\ncustom\n"
