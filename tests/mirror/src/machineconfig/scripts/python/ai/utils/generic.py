from __future__ import annotations

from pathlib import Path

import pytest

import machineconfig.scripts.python.ai.utils.generic as generic_module
import machineconfig.utils.source_of_truth as source_of_truth_module


@pytest.mark.parametrize(
    ("platform_name", "extra_script_name", "path_reference"),
    [
        ("Linux", "lint_and_type_check.sh", generic_module.ai_script_assets.LINT_AND_TYPE_CHECK_SH_PATH_REFERENCE),
        ("Windows", "lint_and_type_check.ps1", generic_module.ai_script_assets.LINT_AND_TYPE_CHECK_PS1_PATH_REFERENCE),
    ],
)
def test_create_dot_scripts_copies_core_and_platform_specific_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform_name: str, extra_script_name: str, path_reference: str
) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()

    monkeypatch.setattr(generic_module.platform, "system", lambda: platform_name)

    generic_module.create_dot_scripts(repo_root=repo_root)

    target_dir = repo_root.joinpath(".ai", "scripts")
    source_dir = generic_module.LIBRARY_ROOT.joinpath("scripts/python/ai/scripts")
    core_script_names = {"lint_and_type_check.py", "lint_and_type_check_models.py", "lint_and_type_check_dashboard.py"}

    for script_name in core_script_names:
        assert target_dir.joinpath(script_name).read_text(encoding="utf-8") == source_dir.joinpath(script_name).read_text(encoding="utf-8")

    source_extra_script = generic_module.get_path_reference_path(module=generic_module.ai_script_assets, path_reference=path_reference)
    assert target_dir.joinpath(extra_script_name).read_text(encoding="utf-8") == source_extra_script.read_text(encoding="utf-8")


def test_create_dot_scripts_rejects_unknown_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(generic_module.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Platform Plan9 is not supported."):
        generic_module.create_dot_scripts(repo_root=tmp_path)


@pytest.mark.parametrize(
    ("platform_name", "input_text", "expected_text"),
    [("Windows", "bash ./tool.sh", "PowerShell .\\tool.ps1"), ("Linux", "PowerShell .\\tool.ps1", "bash ./tool.sh")],
)
def test_adjust_for_os_translates_text_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, platform_name: str, input_text: str, expected_text: str
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
