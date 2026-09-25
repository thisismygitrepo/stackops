import os
import shlex
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_run_interactive_script as scripts
from stackops.utils.sandbox.options import SandboxAccess, SandboxBackend, SandboxOptions
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


@pytest.mark.parametrize("agent", ["codex", "pi"])
def test_interactive_script_keeps_prompt_literal_and_stdin_available(
    agent: AGENTS,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(scripts, "system", lambda: "Linux")
    executable = tmp_path / agent
    executable.write_text(
        """#!/bin/bash
printf '%s\\0' "$@"
IFS= read -r followup
printf '%s\\0' "$followup"
""",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setenv("PATH", os.pathsep.join([str(tmp_path), os.environ["PATH"]]))
    prompt = """# Context
Quotes: 'single' and "double", $HOME, `touch injected`, $(touch injected).

# Prompt
--interactive -i; touch injected
"""
    prompt_file = tmp_path / "prompt with 'quotes'.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    script = scripts.build_interactive_prompt_script(
        agent=agent,
        prompt_file=prompt_file,
        reasoning_effort="none" if agent == "pi" else "high",
        options=SandboxOptions(backend=SandboxBackend.NONE, image=None, settings=None),
    )

    result = subprocess.run(
        ["bash", "-c", script], input="followup input\n", capture_output=True, text=True, check=False, timeout=5,
    )

    assert result.returncode == 0, result.stderr
    arguments = result.stdout.split("\0")[:-1]
    assert arguments[-2:] == [prompt, "followup input"]
    assert "exec" not in arguments
    assert "--mode" not in arguments
    assert "-p" not in arguments
    if agent == "pi":
        assert arguments[arguments.index("--thinking") + 1] == "off"
    else:
        assert '''model_reasoning_effort="high"''' in arguments
        assert "--dangerously-bypass-approvals-and-sandbox" not in arguments
    assert not (tmp_path / "injected").exists()


def test_interactive_script_quotes_powershell_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scripts, "system", lambda: "Windows")
    prompt = """# Context
Keep 'single', "double", $HOME, and $(Write-Output injected).
# Prompt
--interactive
"""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    script = scripts.build_interactive_prompt_script(
        agent="pi",
        prompt_file=prompt_file,
        reasoning_effort=None,
        options=SandboxOptions(backend=SandboxBackend.NONE, image=None, settings=None),
    )

    escaped_prompt = prompt.replace("'", "''")
    assert script == f"""& 'pi' '--' '{escaped_prompt}'"""
    assert "Get-Content" not in script
    assert "agents_run_pi_monitor" not in script


@pytest.mark.parametrize("agent", ["codex", "pi"])
@pytest.mark.parametrize("backend", [SandboxBackend.DOCKER, SandboxBackend.BWRAP])
def test_interactive_sandbox_preserves_tty_and_prompt(
    agent: AGENTS,
    backend: SandboxBackend,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(scripts, "system", lambda: "Linux")
    validation = Mock()
    monkeypatch.setattr(scripts, "validate_prompt_sandbox", validation)
    access = SandboxAccess(writable_paths=(tmp_path / "agent state",), environment_names=(), environment_overrides={})
    access_resolver = Mock(return_value=access)
    monkeypatch.setattr(scripts, "resolve_sandbox_access", access_resolver)
    sandbox_options = SandboxOptions(backend=backend, image="agent-image" if backend == SandboxBackend.DOCKER else None, settings=None)
    captured_commands: list[list[str]] = []

    def capture_sandbox_command(
        *,
        command: list[str],
        options: SandboxOptions,
        directory: Path,
        access: SandboxAccess,
        read_only_paths: tuple[Path, ...],
        interactive: bool,
    ) -> list[str]:
        assert options == sandbox_options
        assert directory == tmp_path
        assert access.writable_paths == (tmp_path / "agent state",)
        assert read_only_paths == ()
        assert interactive is True
        captured_commands.append(command)
        return ["sandbox-wrapper", "--", *command]

    monkeypatch.setattr(scripts, "build_sandbox_command", capture_sandbox_command)
    prompt = """# Context
Sandbox 'quotes' and $(literal).
# Prompt
Continue interactively.
"""
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text(prompt, encoding="utf-8")

    script = scripts.build_interactive_prompt_script(
        agent=agent, prompt_file=prompt_file, reasoning_effort="high", options=sandbox_options,
    )

    validation.assert_called_once_with(agent=agent, options=sandbox_options)
    access_resolver.assert_called_once_with(agent=agent)
    assert len(captured_commands) == 1
    command = captured_commands[0]
    assert command[0] == agent
    assert command[-1] == prompt
    assert "exec" not in command
    assert "--mode" not in command
    assert "-p" not in command
    if agent == "codex":
        assert "--dangerously-bypass-approvals-and-sandbox" in command
    assert shlex.split(script) == ["sandbox-wrapper", "--", *command]
