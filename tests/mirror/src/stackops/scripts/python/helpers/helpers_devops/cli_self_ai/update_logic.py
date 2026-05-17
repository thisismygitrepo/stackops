from pathlib import Path

import pytest
import typer

from stackops.scripts.python.graph import generate_cli_graph
from stackops.scripts.python.helpers.helpers_devops.cli_self_ai import update_logic


def test_update_logic_runs_agents_create_from_repo_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
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
        del agent, model, agent_load, context_path, separator, prompt, prompt_name, job_name
        del join_prompt_and_context, save_as_yaml, host, reasoning, provider, interactive, run
        captured_values["cwd"] = Path.cwd()
        captured_values["context"] = context
        captured_values["prompt_path"] = prompt_path
        captured_values["output_path"] = None if output_path is None else Path(output_path)
        captured_values["agents_dir"] = None if agents_dir is None else Path(agents_dir)

    monkeypatch.setattr(update_logic, "get_developer_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        generate_cli_graph,
        "build_cli_graph",
        lambda: {
            "root": {
                "kind": "root",
                "children": [
                    {
                        "kind": "command",
                        "fullPath": "agents parallel create",
                        "source": {"file": "src/stackops/scripts/python/agents_parallel_commands.py"},
                    }
                ],
            }
        },
    )
    monkeypatch.setattr(update_logic, "agents_create_impl", fake_agents_create_impl)
    monkeypatch.chdir(outside_dir)

    update_logic.update_logic(
        prompt_path="prompts/custom.md",
        agents_dir=".ai/custom-agents",
        output_path=".ai/layouts/custom.json",
    )

    expected_context = "file: src/stackops/scripts/python/agents_parallel_commands.py\ncommand: agents parallel create"
    assert captured_values == {
        "cwd": repo_root,
        "context": expected_context,
        "prompt_path": "prompts/custom.md",
        "output_path": repo_root / ".ai" / "layouts" / "custom.json",
        "agents_dir": repo_root / ".ai" / "custom-agents",
    }
    assert (repo_root / ".ai" / "custom-agents" / "context.md").read_text(encoding="utf-8") == expected_context


def test_update_logic_rejects_non_positive_agent_load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    repo_root.joinpath("pyproject.toml").write_text("", encoding="utf-8")
    monkeypatch.setattr(update_logic, "get_developer_repo_root", lambda: repo_root)

    with pytest.raises(typer.BadParameter, match="--agent-load must be at least 1."):
        update_logic.update_logic(agent_load=0)
