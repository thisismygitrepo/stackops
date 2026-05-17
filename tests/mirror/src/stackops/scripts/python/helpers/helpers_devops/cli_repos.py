from pathlib import Path
import subprocess

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_config_dotfile
from stackops.scripts.python.helpers.helpers_devops import cli_repos


def test_config_linters_writes_to_repo_root_from_nested_directory(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    nested_directory = repo_root.joinpath("nested")
    nested_directory.mkdir(parents=True)
    subprocess.run(["git", "init", "--quiet"], cwd=repo_root, check=True)

    result = CliRunner().invoke(cli_repos.get_app(), ["config-linters", str(nested_directory)])

    assert result.exit_code == 0
    assert repo_root.joinpath(".ruff.toml").exists()
    assert not nested_directory.joinpath(".ruff.toml").exists()
    assert f"✅ Added .ruff.toml to {repo_root}" in result.stdout


def test_config_linters_skips_existing_matching_template(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo_root, check=True)

    template_path = Path(cli_repos.__file__).resolve().parents[4].joinpath("settings", "linters", ".ruff.toml")
    repo_root.joinpath(".ruff.toml").write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")

    result = CliRunner().invoke(cli_repos.get_app(), ["config-linters", "--linter", "ruff", str(repo_root)])

    assert result.exit_code == 0
    assert f"ℹ️ .ruff.toml already matches the template in {repo_root}" in result.stdout


def test_config_linters_refuses_to_overwrite_existing_different_file(tmp_path: Path) -> None:
    repo_root = tmp_path.joinpath("repo")
    repo_root.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo_root, check=True)

    config_path = repo_root.joinpath(".ruff.toml")
    config_path.write_text("custom\n", encoding="utf-8")

    result = CliRunner().invoke(cli_repos.get_app(), ["config-linters", "--linter", "ruff", str(repo_root)])

    assert result.exit_code == 1
    assert f"❌ Refusing to overwrite existing .ruff.toml in {repo_root}. Remove it or update it manually." in result.stdout
    assert config_path.read_text(encoding="utf-8") == "custom\n"


def test_checkout_to_commit_reports_missing_directory(tmp_path: Path) -> None:
    missing_directory = tmp_path.joinpath("missing")

    result = CliRunner().invoke(cli_repos.get_app(), ["checkout-to-commit", str(missing_directory)])

    assert result.exit_code == 1
    assert f"❌ Path does not exist: {missing_directory.resolve()}" in result.output


def test_checkout_to_commit_missing_spec_points_to_sync_specs_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_directory = tmp_path.joinpath("repos")
    repo_directory.mkdir()
    managed_spec_path = tmp_path.joinpath("managed", "repos.json")

    def fake_get_backup_path(*, orig_path: Path, sensitivity: str, destination: str | None, shared: bool) -> Path:
        _ = orig_path, sensitivity, destination, shared
        return managed_spec_path

    monkeypatch.setattr(cli_config_dotfile, "get_backup_path", fake_get_backup_path)

    result = CliRunner().invoke(cli_repos.get_app(), ["checkout-to-commit", str(repo_directory)])

    assert result.exit_code == 1
    assert f"❌ Specification file not found: {managed_spec_path}." in result.output
    assert "Expected a recorded spec for" in result.output
    assert "Use devops repos sync --specs-path <path> to target a spec explicitly." in result.output
    assert "provide it explicitly using --specs-path" not in result.output
