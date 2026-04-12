# pyright: reportPrivateUsage=false
import sys
from types import ModuleType

import pytest

from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive import create_options as create_options_module
from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive import main as main_module


def test_resolve_initial_job_name_keeps_explicit_name_and_randomizes_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_randstr(*, length: int, lower: bool, upper: bool, digits: bool, punctuation: bool) -> str:
        assert length == 3
        assert lower is True
        assert upper is False
        assert digits is False
        assert punctuation is False
        return "xyz"

    monkeypatch.setattr(main_module, "randstr", fake_randstr)

    assert main_module._resolve_initial_job_name("job") == "job"
    assert main_module._resolve_initial_job_name("AI_Agents") == "xyz"
    assert main_module._resolve_initial_job_name(None) == "xyz"


def test_collect_inputs_supports_text_context_and_prompt_name(monkeypatch: pytest.MonkeyPatch) -> None:
    choices = iter(["codex", main_module._CONTEXT_MODE_TEXT, main_module._PROMPT_MODE_NAME])

    def fake_choose_required_option(*, options: tuple[str, ...] | list[str], msg: str, header: str) -> str:
        return next(choices)

    def fake_collect_reviewed_create_options(
        *,
        agent: main_module.AGENTS,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        host: main_module.HOST,
        model: str | None,
        agent_load: int,
        job_name: str,
        reasoning_effort: main_module.ReasoningEffort | None,
        provider: main_module.PROVIDER | None,
    ) -> create_options_module.InteractiveCreateReviewOptions:
        assert agent == "codex"
        assert join_prompt_and_context is False
        assert output_path is None
        assert agents_dir is None
        assert host == "local"
        assert model is None
        assert agent_load == 3
        assert job_name == "job"
        assert reasoning_effort is None
        assert provider is None
        return create_options_module.InteractiveCreateReviewOptions(
            join_prompt_and_context=True,
            output_path="/tmp/layout.json",
            agents_dir="/tmp/agents",
            host="docker",
            model="gpt-5.4",
            agent_load=5,
            job_name="reviewed-job",
            reasoning_effort=None,
            provider="openai",
        )

    def fake_prompt_multiline_text(*, label: str, current: str | None, required: bool) -> str | None:
        assert label == "context"
        assert current is None
        assert required is True
        return "context body"

    def fake_prompt_separator(*, current: str) -> str:
        assert current == "----"
        return "<sep>"

    def fake_prompt_text(*, label: str, current: str | None, required: bool, hint: str) -> str | None:
        assert label == "prompt name"
        assert current == "existing-prompt"
        assert required is True
        assert "prompts YAML lookup" in hint
        return "fresh-prompt"

    monkeypatch.setattr(main_module, "choose_required_option", fake_choose_required_option)
    monkeypatch.setattr(main_module, "collect_reviewed_create_options", fake_collect_reviewed_create_options)
    monkeypatch.setattr(main_module, "prompt_multiline_text", fake_prompt_multiline_text)
    monkeypatch.setattr(main_module, "prompt_separator", fake_prompt_separator)
    monkeypatch.setattr(main_module, "prompt_text", fake_prompt_text)

    result = main_module._collect_inputs(
        agent="copilot",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        host="local",
        model=None,
        reasoning_effort=None,
        provider=None,
        agent_load=3,
        context=None,
        context_path="/tmp/context",
        separator="----",
        prompt=None,
        prompt_path=None,
        prompt_name="existing-prompt",
        job_name="job",
    )

    assert result.agent == "codex"
    assert result.host == "docker"
    assert result.model == "gpt-5.4"
    assert result.provider == "openai"
    assert result.agent_load == 5
    assert result.context == "context body"
    assert result.context_path is None
    assert result.separator == "<sep>"
    assert result.prompt is None
    assert result.prompt_path is None
    assert result.prompt_name == "fresh-prompt"
    assert result.job_name == "reviewed-job"
    assert result.join_prompt_and_context is True
    assert result.output_path == "/tmp/layout.json"
    assert result.agents_dir == "/tmp/agents"


def test_collect_inputs_supports_context_and_prompt_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    choices = iter(["copilot", main_module._CONTEXT_MODE_PATH, main_module._PROMPT_MODE_PATH])
    existing_path_calls: list[tuple[str, bool]] = []

    def fake_choose_required_option(*, options: tuple[str, ...] | list[str], msg: str, header: str) -> str:
        return next(choices)

    def fake_collect_reviewed_create_options(
        *,
        agent: main_module.AGENTS,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        host: main_module.HOST,
        model: str | None,
        agent_load: int,
        job_name: str,
        reasoning_effort: main_module.ReasoningEffort | None,
        provider: main_module.PROVIDER | None,
    ) -> create_options_module.InteractiveCreateReviewOptions:
        assert agent == "copilot"
        assert join_prompt_and_context is False
        assert output_path is None
        assert agents_dir is None
        assert host == "local"
        assert model is None
        assert agent_load == 3
        assert job_name == "job"
        assert reasoning_effort is None
        assert provider is None
        return create_options_module.InteractiveCreateReviewOptions(
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            host="local",
            model=None,
            agent_load=3,
            job_name="job",
            reasoning_effort=None,
            provider=None,
        )

    def fake_prompt_existing_path(*, label: str, current: str | None, must_be_file: bool) -> str:
        existing_path_calls.append((label, must_be_file))
        return "/tmp/context-dir" if label == "context path" else "/tmp/prompt.md"

    def fake_separator_is_applicable_for_context_path(context_path: object) -> bool:
        assert str(context_path) == "/tmp/context-dir"
        return True

    def fake_prompt_separator(*, current: str) -> str:
        assert current == "::"
        return "##"

    monkeypatch.setattr(main_module, "choose_required_option", fake_choose_required_option)
    monkeypatch.setattr(main_module, "collect_reviewed_create_options", fake_collect_reviewed_create_options)
    monkeypatch.setattr(main_module, "prompt_existing_path", fake_prompt_existing_path)
    monkeypatch.setattr(main_module, "separator_is_applicable_for_context_path", fake_separator_is_applicable_for_context_path)
    monkeypatch.setattr(main_module, "prompt_separator", fake_prompt_separator)

    result = main_module._collect_inputs(
        agent="codex",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        host="local",
        model=None,
        reasoning_effort=None,
        provider=None,
        agent_load=3,
        context=None,
        context_path="/tmp/old-context",
        separator="::",
        prompt=None,
        prompt_path="/tmp/old-prompt.md",
        prompt_name=None,
        job_name="job",
    )

    assert existing_path_calls == [("context path", False), ("prompt path", True)]
    assert result.context is None
    assert result.context_path == "/tmp/context-dir"
    assert result.separator == "##"
    assert result.prompt is None
    assert result.prompt_path == "/tmp/prompt.md"
    assert result.prompt_name is None


def test_main_forwards_collected_args_to_agents_create(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_collect_inputs(
        *,
        agent: main_module.AGENTS,
        join_prompt_and_context: bool,
        output_path: str | None,
        agents_dir: str | None,
        host: main_module.HOST,
        model: str | None,
        reasoning_effort: main_module.ReasoningEffort | None,
        provider: main_module.PROVIDER | None,
        agent_load: int,
        context: str | None,
        context_path: str | None,
        separator: str,
        prompt: str | None,
        prompt_path: str | None,
        prompt_name: str | None,
        job_name: str,
    ) -> main_module.InteractiveAgentCreateParams:
        assert agent == "codex"
        assert join_prompt_and_context is False
        assert output_path is None
        assert agents_dir is None
        assert host == "local"
        assert model is None
        assert reasoning_effort is None
        assert provider is None
        assert agent_load == 3
        assert context is None
        assert context_path is None
        assert separator == "::"
        assert prompt is None
        assert prompt_path is None
        assert prompt_name is None
        assert job_name == "job-1"
        return main_module.InteractiveAgentCreateParams(
            agent="codex",
            host="docker",
            model="gpt-5.4",
            reasoning_effort=None,
            provider="openai",
            agent_load=9,
            context="context",
            context_path=None,
            separator="<sep>",
            prompt="prompt",
            prompt_path=None,
            prompt_name=None,
            job_name="job-1",
            join_prompt_and_context=True,
            output_path="/tmp/layout.json",
            agents_dir="/tmp/agents",
        )

    def fake_agents_create(**kwargs: object) -> None:
        captured.update(kwargs)

    fake_agents_module = ModuleType("machineconfig.scripts.python.helpers.helpers_agents.agents_impl")
    setattr(fake_agents_module, "agents_create", fake_agents_create)

    monkeypatch.setattr(main_module, "_collect_inputs", fake_collect_inputs)
    monkeypatch.setitem(sys.modules, "machineconfig.scripts.python.helpers.helpers_agents.agents_impl", fake_agents_module)

    main_module.main(
        agent="codex",
        host="local",
        model=None,
        reasoning_effort=None,
        provider=None,
        agent_load=3,
        context=None,
        context_path=None,
        separator="::",
        prompt=None,
        prompt_path=None,
        prompt_name=None,
        job_name="job-1",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
    )

    assert captured["agent"] == "codex"
    assert captured["host"] == "docker"
    assert captured["model"] == "gpt-5.4"
    assert captured["provider"] == "openai"
    assert captured["agent_load"] == 9
    assert captured["job_name"] == "job-1"
    assert captured["interactive"] is False
