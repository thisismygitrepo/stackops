import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive import main as interactive_main
from stackops.scripts.python.helpers.helpers_agents import agents_ask_impl
from stackops.scripts.python.helpers.helpers_agents import agents_execute_impl
from stackops.scripts.python.helpers.helpers_agents import agents_iter_rich_output
from stackops.scripts.python.helpers.helpers_agents import agents_plan_impl
from stackops.scripts.python.helpers.helpers_agents import agents_run_impl
from stackops.scripts.python.helpers.helpers_agents import agents_skill_impl
from stackops.scripts.python.helpers.helpers_agents import agents_agentops_cache
from stackops.utils.schemas.fire_agents.fire_agents_types import DEFAULT_AGENT
import stackops.utils.accessories as accessories


def _capture_run_prompt(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str | None, object]]:
    captured_calls: list[tuple[str | None, object]] = []

    def fake_run(
        prompt: str | None,
        agent: object,
        reasoning_effort: object,
        context: str | None,
        context_path: str | None,
        prompts_yaml_path: str | None,
        context_name: str | None,
        source: object,
        edit: bool,
        show_prompts_yaml_format: bool,
    ) -> None:
        captured_calls.append((prompt, agent))

    monkeypatch.setattr(agents_run_impl, "run", fake_run)
    return captured_calls


def test_apply_headroom_uses_resolved_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return "/opt/bin/headroom"

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    command = agents._apply_headroom(command=["codex", "--dangerously-bypass-approvals-and-sandbox"], agent="codex", headroom=True)

    assert command == ["/opt/bin/headroom", "wrap", "codex", "--", "--dangerously-bypass-approvals-and-sandbox"]


def test_apply_headroom_rejects_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return None

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    with pytest.raises(ValueError, match="Required command not found: headroom"):
        agents._apply_headroom(command=["codex"], agent="codex", headroom=True)


def test_apply_headroom_rejects_unsupported_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return "/opt/bin/headroom"

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    with pytest.raises(ValueError, match="headroom does not support opencode"):
        agents._apply_headroom(command=["omp"], agent="opencode", headroom=True)


def test_run_prompt_accepts_unquoted_prompt_parts(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls = _capture_run_prompt(monkeypatch=monkeypatch)

    result = CliRunner().invoke(agents.get_app(), ["run-prompt", "inspect", "this", "repo"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("inspect this repo", DEFAULT_AGENT)]


def test_run_prompt_accepts_option_looking_prompt_after_delimiter(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls = _capture_run_prompt(monkeypatch=monkeypatch)

    result = CliRunner().invoke(agents.get_app(), ["run-prompt", "--", "review", "--flag-like", "-x"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("review --flag-like -x", DEFAULT_AGENT)]


def test_parallel_create_context_defaults_to_codex(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured_calls = _capture_run_prompt(monkeypatch=monkeypatch)
    monkeypatch.setattr(accessories, "get_repo_root", lambda path: tmp_path)

    result = CliRunner().invoke(agents.get_app(), ["parallel", "create-context", "split this work", "--job-name", "split-job"])

    assert result.exit_code == 0, result.output
    assert len(captured_calls) == 1
    prompt, agent = captured_calls[0]
    assert agent == DEFAULT_AGENT
    assert prompt is not None
    assert "split this work" in prompt
    assert "./.ai/agents/split-job/context.md" in prompt


def test_ask_defaults_to_shared_default_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_agents: list[object] = []

    def fake_run_ask(prompt_parts: object, agent: object, reasoning: object, file_prompt: object, quiet: bool) -> int:
        captured_agents.append(agent)
        return 0

    monkeypatch.setattr(agents_ask_impl, "run_ask", fake_run_ask)

    result = CliRunner().invoke(agents.get_app(), ["ask", "summarize"])

    assert result.exit_code == 0, result.output
    assert captured_agents == [DEFAULT_AGENT]


def test_plan_defaults_to_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[str, object]] = []

    def fake_run_plan(*, user_prompt: str, agent: object) -> Path:
        captured_calls.append((user_prompt, agent))
        return Path(".ai/plans/build-typed-scheduler.plan.json")

    monkeypatch.setattr(agents_plan_impl, "run_plan", fake_run_plan)

    result = CliRunner().invoke(agents.get_app(), ["plan", "build", "typed", "scheduler"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("build typed scheduler", DEFAULT_AGENT)]
    assert "Plan target: .ai/plans/build-typed-scheduler.plan.json" in result.output


def test_plan_accepts_agent_option(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[tuple[str, object]] = []

    def fake_run_plan(*, user_prompt: str, agent: object) -> Path:
        captured_calls.append((user_prompt, agent))
        return Path(".ai/plans/review-flag-like.plan.json")

    monkeypatch.setattr(agents_plan_impl, "run_plan", fake_run_plan)

    result = CliRunner().invoke(agents.get_app(), ["plan", "--agent", "opencode", "--", "review", "--flag-like"])

    assert result.exit_code == 0, result.output
    assert captured_calls == [("review --flag-like", "opencode")]


def test_plan_prompt_declares_schema_and_agentops_rules(tmp_path: Path) -> None:
    schema = agents_plan_impl.plan_json_schema()
    prompt = agents_plan_impl.build_plan_prompt(
        user_prompt="Improve release workflow",
        plan_path=tmp_path / "improve-release-workflow.plan.json",
        schema_path=tmp_path / "plan.schema.json",
        schema=schema,
    )

    assert '"agentOps"' in prompt
    assert '"parallel-isolated-agents"' in prompt
    assert "Using skill agentops, <agentOps>, work towards" in prompt
    assert "`improve-release-workflow.plan.json`" in prompt
    assert '"successCriteria"' not in prompt
    assert '"outputs"' not in prompt
    assert '"dependsOn"' not in prompt


def test_run_plan_writes_schema_and_dispatches_agent_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_run_agent_prompt(
        prompt: str | None,
        agent: object,
        reasoning_effort: object,
        context: str | None,
        context_path: str | None,
        prompts_yaml_path: str | None,
        context_name: str | None,
        source: object,
        edit: bool,
        show_prompts_yaml_format: bool,
    ) -> None:
        captured_calls.append(
            {
                "prompt": prompt,
                "agent": agent,
                "reasoning_effort": reasoning_effort,
                "context": context,
                "context_path": context_path,
                "prompts_yaml_path": prompts_yaml_path,
                "context_name": context_name,
                "source": source,
                "edit": edit,
                "show_prompts_yaml_format": show_prompts_yaml_format,
            }
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(agents_plan_impl, "run_agent_prompt", fake_run_agent_prompt)

    plan_path = agents_plan_impl.run_plan(user_prompt="Improve release workflow", agent=DEFAULT_AGENT)

    assert tmp_path.joinpath(".ai", "plans", "plan.schema.json").is_file()
    assert plan_path == tmp_path.joinpath(".ai", "plans", "improve-release-workflow.plan.json")
    assert len(captured_calls) == 1
    assert captured_calls[0]["agent"] == DEFAULT_AGENT
    assert captured_calls[0]["context"] == ""
    dispatched_prompt = captured_calls[0]["prompt"]
    assert isinstance(dispatched_prompt, str)
    assert str(tmp_path.joinpath(".ai", "plans", "improve-release-workflow.plan.json")) in dispatched_prompt


def test_plan_short_alias_is_uppercase_p() -> None:
    result = CliRunner().invoke(agents.get_app(), ["P", "--help"])

    assert result.exit_code == 0, result.output
    assert "Generate an agentops plan JSON" in result.output


def test_execute_command_dispatches_impl_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_run_execute(*, plan_path: Path | None, checker_agent: object, interval_seconds: int, once: bool, report: object) -> None:
        captured_calls.append(
            {
                "plan_path": plan_path,
                "checker_agent": checker_agent,
                "interval_seconds": interval_seconds,
                "once": once,
                "report": report,
            }
        )

    plan_path = tmp_path / "example.plan.json"
    monkeypatch.setattr(agents_execute_impl, "run_execute", fake_run_execute)

    result = CliRunner().invoke(agents.get_app(), ["execute", str(plan_path), "--once"])

    assert result.exit_code == 0, result.output
    assert len(captured_calls) == 1
    assert captured_calls[0]["plan_path"] == plan_path
    assert captured_calls[0]["checker_agent"] == DEFAULT_AGENT
    assert captured_calls[0]["interval_seconds"] == agents_execute_impl.EXECUTE_INTERVAL_SECONDS
    assert captured_calls[0]["once"] is True


def test_execute_command_accepts_omitted_plan_path(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_calls: list[dict[str, object]] = []

    def fake_run_execute(*, plan_path: Path | None, checker_agent: object, interval_seconds: int, once: bool, report: object) -> None:
        captured_calls.append(
            {
                "plan_path": plan_path,
                "checker_agent": checker_agent,
                "interval_seconds": interval_seconds,
                "once": once,
                "report": report,
            }
        )

    monkeypatch.setattr(agents_execute_impl, "run_execute", fake_run_execute)

    result = CliRunner().invoke(agents.get_app(), ["execute", "--once"])

    assert result.exit_code == 0, result.output
    assert len(captured_calls) == 1
    assert captured_calls[0]["plan_path"] is None
    assert captured_calls[0]["checker_agent"] == DEFAULT_AGENT
    assert captured_calls[0]["interval_seconds"] == agents_execute_impl.EXECUTE_INTERVAL_SECONDS
    assert captured_calls[0]["once"] is True


def test_execute_resolves_only_generated_plan_when_path_omitted(tmp_path: Path) -> None:
    plan_directory = tmp_path / ".ai" / "plans"
    plan_directory.mkdir(parents=True)
    plan_path = plan_directory / "single.plan.json"
    plan_path.write_text("{}\n", encoding="utf-8")

    resolved = agents_execute_impl.resolve_execute_plan_path(plan_path=None, cwd=tmp_path)

    assert resolved == plan_path


def test_execute_rejects_omitted_path_when_multiple_plans_exist(tmp_path: Path) -> None:
    plan_directory = tmp_path / ".ai" / "plans"
    plan_directory.mkdir(parents=True)
    plan_directory.joinpath("first.plan.json").write_text("{}\n", encoding="utf-8")
    plan_directory.joinpath("second.plan.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="multiple"):
        agents_execute_impl.resolve_execute_plan_path(plan_path=None, cwd=tmp_path)


def test_execute_once_launches_first_pending_phase(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    launched_phases: list[str] = []
    plan_path = _write_example_execute_plan(tmp_path=tmp_path, first_status="pending", second_status="pending")

    def fake_launch_phase_agent(*, plan: object, phase: agents_execute_impl.PlanPhase, plan_path: Path) -> int:
        launched_phases.append(phase["id"])
        return 1001

    monkeypatch.setattr(agents_execute_impl, "launch_phase_agent", fake_launch_phase_agent)

    agents_execute_impl.execute_plan_once(plan_path=plan_path, checker_agent=DEFAULT_AGENT, report=lambda _message: None)

    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    assert updated["phases"][0]["status"] == "running"
    assert updated["phases"][1]["status"] == "pending"
    assert launched_phases == ["phase-001"]


def test_execute_once_completes_running_phase_and_launches_next(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    launched_phases: list[str] = []
    plan_path = _write_example_execute_plan(tmp_path=tmp_path, first_status="running", second_status="pending")

    def fake_ask_phase_finished(
        *, plan: object, phase: agents_execute_impl.PlanPhase, plan_path: Path, checker_agent: object
    ) -> bool:
        return True

    def fake_launch_phase_agent(*, plan: object, phase: agents_execute_impl.PlanPhase, plan_path: Path) -> int:
        launched_phases.append(phase["id"])
        return 1002

    monkeypatch.setattr(agents_execute_impl, "ask_phase_finished", fake_ask_phase_finished)
    monkeypatch.setattr(agents_execute_impl, "launch_phase_agent", fake_launch_phase_agent)

    agents_execute_impl.execute_plan_once(plan_path=plan_path, checker_agent=DEFAULT_AGENT, report=lambda _message: None)

    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    assert updated["phases"][0]["status"] == "completed"
    assert updated["phases"][1]["status"] == "running"
    assert launched_phases == ["phase-002"]


def test_execute_once_keeps_running_phase_when_checker_returns_false(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    plan_path = _write_example_execute_plan(tmp_path=tmp_path, first_status="running", second_status="pending")

    def fake_ask_phase_finished(
        *, plan: object, phase: agents_execute_impl.PlanPhase, plan_path: Path, checker_agent: object
    ) -> bool:
        return False

    monkeypatch.setattr(agents_execute_impl, "ask_phase_finished", fake_ask_phase_finished)

    agents_execute_impl.execute_plan_once(plan_path=plan_path, checker_agent=DEFAULT_AGENT, report=lambda _message: None)

    updated = json.loads(plan_path.read_text(encoding="utf-8"))
    assert updated["phases"][0]["status"] == "running"
    assert updated["phases"][1]["status"] == "pending"


def test_execute_boolean_parser_requires_plain_boolean() -> None:
    assert agents_execute_impl.parse_agent_boolean(output="true\n") is True
    assert agents_execute_impl.parse_agent_boolean(output="false") is False
    with pytest.raises(ValueError, match="exactly true or false"):
        agents_execute_impl.parse_agent_boolean(output="The answer is true.")


def test_execute_short_alias_is_uppercase_e() -> None:
    result = CliRunner().invoke(agents.get_app(), ["E", "--help"])

    assert result.exit_code == 0, result.output
    assert "Execute an agentops plan JSON" in result.output


def test_interactive_create_defaults_to_codex() -> None:
    assert interactive_main.main.__kwdefaults__ is not None
    assert interactive_main.main.__kwdefaults__["agent"] == DEFAULT_AGENT


def _write_example_execute_plan(*, tmp_path: Path, first_status: str, second_status: str) -> Path:
    plan_path = tmp_path / "example.plan.json"
    plan = {
        "$schema": "./plan.schema.json",
        "schemaVersion": 1,
        "slug": "example",
        "objective": "Build example",
        "phases": [
            {
                "id": "phase-001",
                "title": "First",
                "status": first_status,
                "agent": DEFAULT_AGENT,
                "agentOps": "handover",
                "task": "Using skill agentops, handover, work towards first phase.",
            },
            {
                "id": "phase-002",
                "title": "Second",
                "status": second_status,
                "agent": DEFAULT_AGENT,
                "agentOps": None,
                "task": "Run second phase.",
            },
        ],
    }
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return plan_path


def test_add_config_reports_plan_phases_and_files(tmp_path: Path) -> None:
    result = CliRunner().invoke(agents.get_app(), ["add-config", "--agent", "codex", "--root", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Agent configuration plan" in result.output
    assert "Configured codex" in result.output
    assert "Configuration complete" in result.output
    assert "Filesystem changes (2)" in result.output
    assert "./.codex/config.toml" in result.output
    assert "./AGENTS.md" in result.output
    config_content = tmp_path.joinpath(".codex", "config.toml").read_text(encoding="utf-8")
    assert "[otel]" not in config_content
    assert "remote_models" not in config_content


def test_add_config_short_alias_is_c(tmp_path: Path) -> None:
    result = CliRunner().invoke(agents.get_app(), ["c", "--agent", "codex", "--root", str(tmp_path), "--no-add-instructions"])

    assert result.exit_code == 0, result.output
    assert tmp_path.joinpath(".codex", "config.toml").is_file()


def test_iter_status_command_calls_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_show_iter_status() -> None:
        calls.append("status")

    monkeypatch.setattr(agents_iter_rich_output, "show_iter_status", fake_show_iter_status)

    result = CliRunner().invoke(agents.get_app(), ["iter", "status"])

    assert result.exit_code == 0, result.output
    assert calls == ["status"]


def test_iter_close_command_calls_impl_for_one_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, bool, bool]] = []

    def fake_close_iter_workspaces_loop(
        *, workspace_name: str | None, all_workspaces: bool, continuous: bool
    ) -> None:
        calls.append((workspace_name, all_workspaces, continuous))

    monkeypatch.setattr(agents_iter_rich_output, "show_close_iter_workspaces_loop", fake_close_iter_workspaces_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "close", "iter-alpha"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", False, False)]


def test_iter_close_all_command_calls_impl_for_all_workspaces(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str | None, bool, bool]] = []

    def fake_close_iter_workspaces_loop(
        *, workspace_name: str | None, all_workspaces: bool, continuous: bool
    ) -> None:
        calls.append((workspace_name, all_workspaces, continuous))

    monkeypatch.setattr(agents_iter_rich_output, "show_close_iter_workspaces_loop", fake_close_iter_workspaces_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "close", "--all", "--loop"])

    assert result.exit_code == 0, result.output
    assert calls == [(None, True, True)]


def test_iter_clean_command_calls_cache_impl(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Path] = []

    def fake_clean_agentops_cache(*, cwd: Path, report: object) -> agents_agentops_cache.AgentopsCacheCleanResult:
        calls.append(cwd)
        return agents_agentops_cache.AgentopsCacheCleanResult(
            repo_root=cwd,
            cache_path=cwd.joinpath(".ai", "agentops"),
            removed=False,
            removed_entries=0,
        )

    monkeypatch.setattr(agents_iter_rich_output, "clean_agentops_cache", fake_clean_agentops_cache)

    result = CliRunner().invoke(agents.get_app(), ["iter", "clean"])

    assert result.exit_code == 0, result.output
    assert len(calls) == 1


def test_iter_track_command_calls_impl_with_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, int, bool]] = []

    def fake_track_iter_workspace_loop(
        *, workspace_name: str, max_iterations: int, interval_seconds: int, close_old_tabs: bool
    ) -> None:
        calls.append((workspace_name, max_iterations, interval_seconds, close_old_tabs))

    monkeypatch.setattr(agents_iter_rich_output, "show_track_iter_workspace_loop", fake_track_iter_workspace_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "track", "iter-alpha"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", 100, 60, False)]


def test_iter_track_command_accepts_budget_and_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, int, bool]] = []

    def fake_track_iter_workspace_loop(
        *, workspace_name: str, max_iterations: int, interval_seconds: int, close_old_tabs: bool
    ) -> None:
        calls.append((workspace_name, max_iterations, interval_seconds, close_old_tabs))

    monkeypatch.setattr(agents_iter_rich_output, "show_track_iter_workspace_loop", fake_track_iter_workspace_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "track", "iter-alpha", "7", "--interval", "2"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", 7, 2, False)]


def test_iter_track_command_accepts_close_old_tabs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, int, int, bool]] = []

    def fake_track_iter_workspace_loop(
        *, workspace_name: str, max_iterations: int, interval_seconds: int, close_old_tabs: bool
    ) -> None:
        calls.append((workspace_name, max_iterations, interval_seconds, close_old_tabs))

    monkeypatch.setattr(agents_iter_rich_output, "show_track_iter_workspace_loop", fake_track_iter_workspace_loop)

    result = CliRunner().invoke(agents.get_app(), ["iter", "track", "iter-alpha", "--close-old-tabs"])

    assert result.exit_code == 0, result.output
    assert calls == [("iter-alpha", 100, 60, True)]


def test_iter_short_alias_is_uppercase_i() -> None:
    result = CliRunner().invoke(agents.get_app(), ["I", "--help"])

    assert result.exit_code == 0, result.output
    assert "Iter workflow maintenance" in result.output
    assert "clean" in result.output
    assert "close" in result.output


def test_add_skill_short_alias_is_s() -> None:
    result = CliRunner().invoke(agents.get_app(), ["s", "--help"])

    assert result.exit_code == 0, result.output
    assert "Add a skill" in result.output


def test_add_skill_default_backend_is_stackops(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    observed: dict[str, object] = {}

    def fake_add_skill(
        *,
        skill_name: str | None,
        agent: str | None,
        scope: object,
        directory: str | None,
        backend: object,
        yes: bool,
    ) -> int:
        observed["skill_name"] = skill_name
        observed["agent"] = agent
        observed["scope"] = scope
        observed["directory"] = directory
        observed["backend"] = backend
        observed["yes"] = yes
        return 0

    monkeypatch.setattr(agents_skill_impl, "add_skill", fake_add_skill)

    result = CliRunner().invoke(agents.get_app(), ["add-skill", "stackops", "--directory", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert observed == {
        "skill_name": "stackops",
        "agent": None,
        "scope": "local",
        "directory": str(tmp_path),
        "backend": "stackops",
        "yes": False,
    }


def test_removed_todo_and_symlink_commands_are_not_registered() -> None:
    runner = CliRunner()
    help_result = runner.invoke(agents.get_app(), ["--help"])

    assert help_result.exit_code == 0, help_result.output
    assert "add-todo" not in help_result.output
    assert "add-symlinks" not in help_result.output

    for removed_command in ("add-todo", "d", "add-symlinks", "L"):
        result = runner.invoke(agents.get_app(), [removed_command, "--help"])
        assert result.exit_code != 0, result.output
        assert f"No such command '{removed_command}'" in result.output
