from pathlib import Path

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python.helpers.helpers_devops import cli_self, cli_self_ai


def test_self_help_shows_ai_only_for_developers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    home_root = tmp_path.joinpath("home", "alex")
    monkeypatch.setattr(cli_self.Path, "home", lambda: home_root)

    result_without_repo = runner.invoke(cli_self.get_app(), ["--help"])

    assert result_without_repo.exit_code == 0
    assert "Developer AI workflows" not in result_without_repo.stdout

    repo_root = home_root.joinpath("code", "machineconfig")
    repo_root.mkdir(parents=True, exist_ok=True)
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'machineconfig'\n", encoding="utf-8")

    result_with_repo = runner.invoke(cli_self.get_app(), ["a", "--help"])

    assert result_with_repo.exit_code == 0
    assert "update-installer" in result_with_repo.stdout
    assert "update-test" in result_with_repo.stdout


def test_update_installer_uses_embedded_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_root = tmp_path.joinpath("home", "alex")
    repo_root = home_root.joinpath("code", "machineconfig")
    repo_root.mkdir(parents=True, exist_ok=True)
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'machineconfig'\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli_self_ai.Path, "home", lambda: home_root)
    monkeypatch.setattr(cli_self_ai, "agents_create_impl", fake_agents_create_impl)

    cli_self_ai.update_installer()

    job_name = "updateInstallerData"
    agents_dir = repo_root.joinpath(".ai", "agents", job_name)

    assert captured["agent"] == "codex"
    assert captured["host"] == "local"
    assert captured["context"] is None
    assert captured["context_path"] == str(repo_root.joinpath("src", "machineconfig", "jobs", "installer", "installer_data.json"))
    assert captured["separator"] == "    },\n    {"
    assert captured["agent_load"] == 10
    assert captured["prompt"] == cli_self_ai.UPDATE_INSTALLER_PROMPT
    assert captured["prompt_path"] is None
    assert captured["prompt_name"] is None
    assert captured["job_name"] == job_name
    assert captured["output_path"] == str(agents_dir.joinpath("layout.json"))
    assert captured["agents_dir"] == str(agents_dir)
    assert captured["interactive"] is False


def test_update_installer_allows_overriding_default_sources_and_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_root = tmp_path.joinpath("home", "alex")
    repo_root = home_root.joinpath("code", "machineconfig")
    repo_root.mkdir(parents=True, exist_ok=True)
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'machineconfig'\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli_self_ai.Path, "home", lambda: home_root)
    monkeypatch.setattr(cli_self_ai, "agents_create_impl", fake_agents_create_impl)

    cli_self_ai.update_installer(agent="gemini", context="context body", prompt="prompt body", job_name="customJob")

    custom_agents_dir = repo_root.joinpath(".ai", "agents", "customJob")

    assert captured["agent"] == "gemini"
    assert captured["context"] == "context body"
    assert captured["context_path"] is None
    assert captured["prompt"] == "prompt body"
    assert captured["prompt_path"] is None
    assert captured["job_name"] == "customJob"
    assert captured["agents_dir"] == str(custom_agents_dir)
    assert captured["output_path"] == str(custom_agents_dir.joinpath("layout.json"))


def test_update_test_uses_embedded_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home_root = tmp_path.joinpath("home", "alex")
    repo_root = home_root.joinpath("code", "machineconfig")
    repo_root.mkdir(parents=True, exist_ok=True)
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'machineconfig'\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_agents_create_impl(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(cli_self_ai.Path, "home", lambda: home_root)
    monkeypatch.setattr(cli_self_ai, "agents_create_impl", fake_agents_create_impl)

    cli_self_ai.update_test()

    job_name = "updateTests"
    agents_dir = repo_root.joinpath(".ai", "agents", job_name)

    assert captured["agent"] == "codex"
    assert captured["host"] == "local"
    assert captured["context"] is None
    assert captured["context_path"] == str(repo_root.joinpath(".ai", "todo"))
    assert captured["separator"] == "    },\n    {"
    assert captured["agent_load"] == 10
    assert captured["prompt"] == cli_self_ai.UPDATE_TEST_PROMPT
    assert captured["prompt_path"] is None
    assert captured["prompt_name"] is None
    assert captured["job_name"] == job_name
    assert captured["output_path"] == str(agents_dir.joinpath("layout.json"))
    assert captured["agents_dir"] == str(agents_dir)
    assert captured["interactive"] is False
