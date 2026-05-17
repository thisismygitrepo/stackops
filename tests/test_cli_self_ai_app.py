

from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import update_docs as update_docs_module
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai.app import get_app
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai.update_docs import should_include_docs_context_path


def test_workflow_help_lists_update_docs_command() -> None:
    runner = CliRunner()
    result = runner.invoke(get_app(), ["--help"])

    assert result.exit_code == 0
    assert "update-docs" in result.stdout
    assert "Create an agents layout for updating CLI and API" in result.stdout
    assert "docs only." in result.stdout
    assert "update-logic" in result.stdout


def test_update_docs_context_is_limited_to_cli_and_api_docs() -> None:
    assert should_include_docs_context_path(relative_path=Path("docs/cli/devops.md"))
    assert should_include_docs_context_path(relative_path=Path("docs/api/index.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/index.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/guide/overview.md"))
    assert not should_include_docs_context_path(relative_path=Path("docs/assets/before.png"))


def test_update_docs_runs_agents_create_from_repo_root(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'stackops'\n", encoding="utf-8")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    captured_values: dict[str, Path | str | None] = {}

    def fake_build_docs_context(*, repo_root: Path) -> str:
        captured_values["build_docs_context_repo_root"] = repo_root
        return "docs/cli/devops.md"

    def fake_agents_create_impl(
        *,
        agent: object,
        model: object,
        agent_load: object,
        context: object,
        context_path: object,
        separator: object,
        prompt: object,
        prompt_path: object,
        prompt_name: object,
        job_name: object,
        join_prompt_and_context: object,
        output_path: object,
        agents_dir: object,
        save_as_yaml: object,
        host: object,
        reasoning: object,
        provider: object,
        interactive: object,
        run: object,
    ) -> None:
        del (
            agent,
            model,
            agent_load,
            context,
            context_path,
            separator,
            prompt,
            prompt_name,
            job_name,
            join_prompt_and_context,
            output_path,
            agents_dir,
            save_as_yaml,
            host,
            reasoning,
            provider,
            interactive,
            run,
        )
        captured_values["cwd_during_agents_create"] = Path.cwd()
        captured_values["prompt_path"] = prompt_path if isinstance(prompt_path, str) else None

    monkeypatch.setattr(update_docs_module, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_docs_module, "_build_docs_context", fake_build_docs_context)
    monkeypatch.setattr(update_docs_module, "agents_create_impl", fake_agents_create_impl)
    monkeypatch.chdir(outside_dir)

    update_docs_module.update_docs(prompt_path="prompts/update_docs.txt")

    assert captured_values["build_docs_context_repo_root"] == repo_root
    assert captured_values["cwd_during_agents_create"] == repo_root
    assert captured_values["prompt_path"] == "prompts/update_docs.txt"
    assert (repo_root / ".ai" / "agents" / update_docs_module.DEFAULT_DOCS_JOB_NAME / "context.md").read_text(encoding="utf-8") == (
        "docs/cli/devops.md"
    )


def test_update_docs_resolves_relative_paths_from_repo_root(monkeypatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("[project]\nname = 'stackops'\n", encoding="utf-8")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    captured_values: dict[str, Path] = {}

    def fake_build_docs_context(*, repo_root: Path) -> str:
        del repo_root
        return "docs/cli/devops.md"

    def fake_agents_create_impl(
        *,
        agent: object,
        model: object,
        agent_load: object,
        context: object,
        context_path: object,
        separator: object,
        prompt: object,
        prompt_path: object,
        prompt_name: object,
        job_name: object,
        join_prompt_and_context: object,
        output_path: object,
        agents_dir: object,
        save_as_yaml: object,
        host: object,
        reasoning: object,
        provider: object,
        interactive: object,
        run: object,
    ) -> None:
        del (
            agent,
            model,
            agent_load,
            context,
            context_path,
            separator,
            prompt,
            prompt_path,
            prompt_name,
            job_name,
            join_prompt_and_context,
            save_as_yaml,
            host,
            reasoning,
            provider,
            interactive,
            run,
        )
        captured_values["agents_dir"] = Path(str(agents_dir))
        captured_values["output_path"] = Path(str(output_path))

    monkeypatch.setattr(update_docs_module, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_docs_module, "_build_docs_context", fake_build_docs_context)
    monkeypatch.setattr(update_docs_module, "agents_create_impl", fake_agents_create_impl)
    monkeypatch.chdir(outside_dir)

    update_docs_module.update_docs(agents_dir="relative/agents", output_path="relative/layout.json")

    assert captured_values["agents_dir"] == repo_root / "relative" / "agents"
    assert captured_values["output_path"] == repo_root / "relative" / "layout.json"
    assert (repo_root / "relative" / "agents" / "context.md").read_text(encoding="utf-8") == "docs/cli/devops.md"
    assert not (outside_dir / "relative" / "agents" / "context.md").exists()
