import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from machineconfig.scripts.python import agents
from machineconfig.scripts.python.ai.initai import add_ai_configs
from machineconfig.scripts.python.helpers.helpers_agents import agents_impl
from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive import common as interactive_common
from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive import create_options as interactive_create_options
from machineconfig.scripts.python.helpers.helpers_agents.agent_impl_interactive import main as interactive_main
from machineconfig.scripts.python.helpers.helpers_agents.agentic_frameworks.fire_codex import fire_codex
from machineconfig.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC, API_SPEC, DEFAULT_SEAPRATOR
from machineconfig.scripts.python.helpers.helpers_agents.reasoning_capabilities import ReasoningEffort


runner = CliRunner()


def _make_codex_ai_spec(*, reasoning_effort: ReasoningEffort | None) -> AI_SPEC:
    return AI_SPEC(
        provider="openai",
        model="gpt-5.4",
        agent="codex",
        machine="local",
        api_spec=API_SPEC(api_key=None, api_name="", api_label="", api_account=""),
        reasoning_effort=reasoning_effort,
    )


def test_parallel_create_help_includes_reasoning_effort_option() -> None:
    result = runner.invoke(agents.get_app(), ["parallel", "create", "--help"])

    assert result.exit_code == 0
    assert "--reasoning-effort" in result.output
    assert "-r" in result.output


def test_parallel_create_passes_reasoning_effort_to_impl() -> None:
    with patch("machineconfig.scripts.python.helpers.helpers_agents.agents_impl.agents_create") as impl:
        result = runner.invoke(
            agents.get_app(),
            [
                "parallel",
                "create",
                "--agent",
                "codex",
                "--prompt",
                "inspect the repo",
                "--context",
                "task one",
                "--reasoning-effort",
                "high",
            ],
        )

    assert result.exit_code == 0
    impl.assert_called_once_with(
        agent="codex",
        host="local",
        model=None,
        reasoning_effort="high",
        provider=None,
        context="task one",
        context_path=None,
        separator=DEFAULT_SEAPRATOR,
        agent_load=3,
        prompt="inspect the repo",
        prompt_path=None,
        job_name="AI_Agents",
        join_prompt_and_context=False,
        output_path=None,
        agents_dir=None,
        interactive=False,
    )


def test_parallel_create_decodes_separator_escape_sequences() -> None:
    with patch("machineconfig.scripts.python.helpers.helpers_agents.agents_impl.agents_create") as impl:
        result = runner.invoke(
            agents.get_app(),
            [
                "parallel",
                "create",
                "--prompt",
                "inspect the repo",
                "--context",
                "task one",
                "--separator",
                r"\n---\n",
            ],
        )

    assert result.exit_code == 0
    assert impl.call_args.kwargs["separator"] == "\n---\n"


def test_agents_impl_rejects_reasoning_effort_for_non_codex() -> None:
    with pytest.raises(ValueError, match="only supported for --agent codex"):
        agents_impl.agents_create(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort="high",
            provider=None,
            context="task one",
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            agent_load=1,
            prompt="inspect the repo",
            prompt_path=None,
            job_name="AI_Agents",
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            interactive=False,
        )


def test_fire_codex_includes_reasoning_effort_config() -> None:
    repo_root = Path("/workspace/repo")
    prompt_path = repo_root / "prompts" / "agent_0_prompt.txt"

    command = fire_codex(ai_spec=_make_codex_ai_spec(reasoning_effort="high"), prompt_path=prompt_path, repo_root=repo_root)

    assert """-c 'model_reasoning_effort="high"'""" in command


def test_fire_codex_omits_reasoning_effort_config_when_not_requested() -> None:
    repo_root = Path("/workspace/repo")
    prompt_path = repo_root / "prompts" / "agent_0_prompt.txt"

    command = fire_codex(ai_spec=_make_codex_ai_spec(reasoning_effort=None), prompt_path=prompt_path, repo_root=repo_root)

    assert "model_reasoning_effort" not in command


def test_interactive_context_directory_with_multiple_text_files_skips_separator_prompt(tmp_path: Path) -> None:
    context_root = tmp_path / "context"
    context_root.mkdir()
    context_root.joinpath("a.md").write_text("one", encoding="utf-8")
    context_root.joinpath("b.txt").write_text("two", encoding="utf-8")

    assert interactive_common.separator_is_applicable_for_context_path(context_root) is False


def test_prompt_separator_uses_editor_and_decodes_escape_sequences(tmp_path: Path) -> None:
    scratch_path = tmp_path / "separator.txt"

    def _fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        scratch_path.write_text(r"\n---\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=0)

    with (
        patch.object(interactive_common, "_discover_editor_command", return_value=["fake-editor"]),
        patch.object(interactive_common, "_editor_scratch_path", return_value=scratch_path),
        patch.object(interactive_common.subprocess, "run", side_effect=_fake_run),
    ):
        separator = interactive_common.prompt_separator(current=DEFAULT_SEAPRATOR)

    assert separator == "\n---\n"
    assert scratch_path.exists() is False


def test_prompt_separator_keeps_current_when_editor_result_is_blank(tmp_path: Path) -> None:
    scratch_path = tmp_path / "separator.txt"

    def _fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        _ = check
        scratch_path.write_text("\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=command, returncode=0)

    with (
        patch.object(interactive_common, "_discover_editor_command", return_value=["fake-editor"]),
        patch.object(interactive_common, "_editor_scratch_path", return_value=scratch_path),
        patch.object(interactive_common.subprocess, "run", side_effect=_fake_run),
    ):
        separator = interactive_common.prompt_separator(current=DEFAULT_SEAPRATOR)

    assert separator == DEFAULT_SEAPRATOR
    assert scratch_path.exists() is False


def test_interactive_main_collects_values_and_delegates() -> None:
    collected = interactive_main.InteractiveAgentCreateParams(
        agent="codex",
        host="docker",
        model="gpt-5.4",
        reasoning_effort="high",
        provider="openai",
        agent_load=5,
        context=None,
        context_path="/tmp/context",
        separator=DEFAULT_SEAPRATOR,
        prompt="inspect the repo",
        prompt_path=None,
        job_name="abc",
        join_prompt_and_context=True,
        output_path="/tmp/layout.json",
        agents_dir="/tmp/agents",
    )

    with (
        patch.object(interactive_main, "randstr", return_value="abc"),
        patch.object(interactive_main, "_collect_inputs", return_value=collected) as collect_inputs,
        patch("machineconfig.scripts.python.helpers.helpers_agents.agents_impl.agents_create") as impl,
    ):
        interactive_main.main(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort=None,
            provider=None,
            agent_load=3,
            context="existing context",
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            prompt=None,
            prompt_path="/tmp/prompt.md",
            job_name="AI_Agents",
            join_prompt_and_context=True,
            output_path="/tmp/layout.json",
            agents_dir="/tmp/agents",
        )

    collect_inputs.assert_called_once_with(
        agent="copilot",
        join_prompt_and_context=True,
        output_path="/tmp/layout.json",
        agents_dir="/tmp/agents",
        host="local",
        model=None,
        reasoning_effort=None,
        provider=None,
        agent_load=3,
        context="existing context",
        context_path=None,
        separator=DEFAULT_SEAPRATOR,
        prompt=None,
        prompt_path="/tmp/prompt.md",
        job_name="abc",
    )
    impl.assert_called_once_with(
        agent="codex",
        host="docker",
        model="gpt-5.4",
        reasoning_effort="high",
        provider="openai",
        agent_load=5,
        context=None,
        context_path="/tmp/context",
        separator=DEFAULT_SEAPRATOR,
        prompt="inspect the repo",
        prompt_path=None,
        job_name="abc",
        join_prompt_and_context=True,
        output_path="/tmp/layout.json",
        agents_dir="/tmp/agents",
        interactive=False,
    )


def test_collect_reviewed_create_options_uses_textual_form_and_updates_selected_values() -> None:
    with (
        patch.object(
            interactive_create_options,
            "use_textual_options_form",
            return_value={
                "join_prompt_and_context = False": False,
                "output_path = auto: layout.json inside agents_dir": "/tmp/layout.json",
                "agents_dir = auto: .ai/agents derived from job_name": None,
                "host = local": "local",
                "model = agent default": "gpt-5.4",
                "agent_load = 3": "5",
                "job_name = abc": "custom-job",
                "reasoning_effort = agent default": None,
                "provider = auto: openai": "openai",
            },
        ) as use_textual_options_form,
    ):
        reviewed = interactive_create_options.collect_reviewed_create_options(
            agent="codex",
            join_prompt_and_context=False,
            output_path=None,
            agents_dir=None,
            host="local",
            model=None,
            agent_load=3,
            job_name="abc",
            reasoning_effort=None,
            provider=None,
        )

    assert reviewed == interactive_create_options.InteractiveCreateReviewOptions(
        join_prompt_and_context=False,
        output_path="/tmp/layout.json",
        agents_dir=None,
        host="local",
        model="gpt-5.4",
        agent_load=5,
        job_name="custom-job",
        reasoning_effort=None,
        provider="openai",
    )
    form_options = use_textual_options_form.call_args.kwargs["options"]
    assert form_options["join_prompt_and_context = False"]["default"] is False
    assert form_options["output_path = auto: layout.json inside agents_dir"] == {
        "kind": "text",
        "default": None,
        "allow_blank": True,
        "placeholder": "Leave blank to auto-create layout.json inside agents_dir",
    }
    assert form_options["model = agent default"] == {
        "kind": "text",
        "default": None,
        "allow_blank": True,
        "placeholder": "Leave blank to use the agent default model",
    }
    assert form_options["agent_load = 3"] == {
        "kind": "text",
        "default": "3",
        "allow_blank": False,
        "placeholder": "Enter a positive integer",
    }
    assert form_options["job_name = abc"] == {
        "kind": "text",
        "default": "abc",
        "allow_blank": False,
        "placeholder": "Enter the job name",
    }
    assert form_options["provider = auto: openai"]["options"] == [None, "openai"]


def test_agents_impl_persists_recreate_artifacts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    agents_dir = repo_root / ".ai" / "agents" / "persisted-dir"
    output_path = repo_root / "layout-out.json"

    with patch("machineconfig.utils.accessories.get_repo_root", return_value=repo_root):
        agents_impl.agents_create(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort=None,
            provider=None,
            context="task one\n---\ntask two",
            context_path=None,
            separator="\n---\n",
            agent_load=1,
            prompt="inspect the repo",
            prompt_path=None,
            job_name="persisted",
            join_prompt_and_context=False,
            output_path=str(output_path),
            agents_dir=str(agents_dir),
            interactive=False,
        )

    artifacts_dir = agents_dir / ".create"
    manifest_path = artifacts_dir / "manifest.json"
    prompt_snapshot_path = artifacts_dir / "prompt.md"
    context_snapshot_path = artifacts_dir / "context.md"
    recreate_script_path = artifacts_dir / "recreate_layout.sh"

    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8"))["layouts"][0]["layoutName"] == "persisted"
    assert prompt_snapshot_path.read_text(encoding="utf-8") == "inspect the repo"
    assert context_snapshot_path.read_text(encoding="utf-8") == "task one\n---\ntask two"
    assert recreate_script_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["job_name"] == "persisted"
    assert manifest["prompt"]["source_kind"] == "inline_text"
    assert manifest["context"]["source_kind"] == "inline_text"
    assert manifest["prompt"]["snapshot_path"] == str(prompt_snapshot_path)
    assert manifest["context"]["snapshot_path"] == str(context_snapshot_path)
    assert manifest["separator_cli_value"] == r"\n---\n"
    assert manifest["recreate_command_args"] == [
        "uv",
        "run",
        "agents",
        "parallel",
        "create",
        "--agent",
        "copilot",
        "--host",
        "local",
        "--context-path",
        str(context_snapshot_path),
        "--separator",
        r"\n---\n",
        "--agent-load",
        "1",
        "--prompt-path",
        str(prompt_snapshot_path),
        "--job-name",
        "persisted",
        "--output-path",
        str(output_path.resolve()),
        "--agents-dir",
        str(agents_dir),
    ]


def test_agents_impl_can_recreate_from_snapshots_inside_agents_dir(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    agents_dir = repo_root / ".ai" / "agents" / "persisted"
    output_path = repo_root / "layout-out.json"

    with patch("machineconfig.utils.accessories.get_repo_root", return_value=repo_root):
        agents_impl.agents_create(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort=None,
            provider=None,
            context="task one",
            context_path=None,
            separator=DEFAULT_SEAPRATOR,
            agent_load=1,
            prompt="inspect the repo",
            prompt_path=None,
            job_name="persisted",
            join_prompt_and_context=False,
            output_path=str(output_path),
            agents_dir=str(agents_dir),
            interactive=False,
        )

        agents_impl.agents_create(
            agent="copilot",
            host="local",
            model=None,
            reasoning_effort=None,
            provider=None,
            context=None,
            context_path=str(agents_dir / ".create" / "context.md"),
            separator=DEFAULT_SEAPRATOR,
            agent_load=1,
            prompt=None,
            prompt_path=str(agents_dir / ".create" / "prompt.md"),
            job_name="persisted",
            join_prompt_and_context=False,
            output_path=str(output_path),
            agents_dir=str(agents_dir),
            interactive=False,
        )

    assert output_path.exists()
    assert (agents_dir / ".create" / "prompt.md").exists()
    assert (agents_dir / ".create" / "context.md").exists()


def test_add_ai_configs_supports_forge(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    add_ai_configs(
        repo_root=repo_root,
        frameworks=("forge",),
        include_common_scaffold=False,
        add_all_touched_configs_to_gitignore=False,
        add_vscode_task=False,
        add_private_config=True,
        add_instructions=True,
    )

    assert repo_root.joinpath("AGENTS.md").exists()
    assert repo_root.joinpath("forge.yaml").read_text(encoding="utf-8") == (
        "# yaml-language-server: $schema=https://raw.githubusercontent.com/antinomyhq/forge/main/forge.schema.json\n"
    )
    assert json.loads(repo_root.joinpath(".mcp.json").read_text(encoding="utf-8")) == {"mcpServers": {}}
