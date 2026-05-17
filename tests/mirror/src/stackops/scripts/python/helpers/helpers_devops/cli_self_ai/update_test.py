from pathlib import Path

import pytest
import typer

from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import update_test


def test_update_test_runs_agents_create_from_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    prompt_path = repo_root / "prompts" / "custom.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("prompt", encoding="utf-8")
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()

    captured_values: dict[str, Path | str | None] = {}

    def fake_agents_create_impl(
        *,
        agent: str,
        model: str | None,
        agent_load: int,
        context: str | None,
        context_path: str | None,
        separator: str,
        prompt: str | None,
        prompt_path: str | None,
        prompt_name: str | None,
        job_name: str | None,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        save_as_yaml: bool,
        host: str,
        reasoning: object,
        provider: str | None,
        interactive: bool,
        run: bool,
    ) -> None:
        del agent, model, agent_load, context, context_path, separator, prompt, prompt_name, job_name
        del join_prompt_and_context, output_path, agents_dir, save_as_yaml, host, reasoning, provider, interactive, run
        captured_values["cwd"] = Path.cwd()
        captured_values["prompt_path"] = prompt_path

    monkeypatch.setattr(update_test, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(update_test, "_build_repo_python_context", lambda *, repo_root: "src/example.py")
    monkeypatch.setattr(update_test, "agents_create_impl", fake_agents_create_impl)
    monkeypatch.chdir(outside_dir)

    update_test.update_test(prompt_path="prompts/custom.md")

    assert captured_values == {
        "cwd": repo_root,
        "prompt_path": "prompts/custom.md",
    }


def test_update_test_rejects_non_positive_agent_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(update_test, "get_developer_repo_root", lambda: repo_root)

    with pytest.raises(typer.BadParameter, match="--agent-load must be at least 1."):
        update_test.update_test(agent_load=0)
