from __future__ import annotations

from pathlib import Path

import machineconfig.scripts.python.ai.solutions.copilot as copilot_assets
from machineconfig.scripts.python.ai.solutions.copilot.github_copilot import build_configuration
from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


def _copilot_root() -> Path:
    return Path(copilot_assets.__file__).resolve().parent


def test_build_configuration_writes_private_assets_into_github_directory(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=False)

    agents_dir = tmp_path.joinpath(".github", "agents")
    prompts_dir = tmp_path.joinpath(".github", "prompts")

    assert sorted(path.name for path in agents_dir.iterdir()) == [
        "Thinking-Beast-Mode.agent.md",
        "Ultimate-Transparent-Thinking-Beast-Mode.agent.md",
        "__init__.agent.md",
        "deepResearch.agent.md",
    ]
    assert sorted(path.name for path in prompts_dir.iterdir()) == [
        "__init__.prompt.md",
        "pyright_fix.prompt.md",
        "research-report-skeleton.prompt.md",
    ]
    assert agents_dir.joinpath("Thinking-Beast-Mode.agent.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "agents", "Thinking-Beast-Mode.agent.md"
    ).read_text(encoding="utf-8")
    assert agents_dir.joinpath("Ultimate-Transparent-Thinking-Beast-Mode.agent.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "agents", "Ultimate-Transparent-Thinking-Beast-Mode.agent.md"
    ).read_text(encoding="utf-8")
    assert agents_dir.joinpath("__init__.agent.md").read_text(encoding="utf-8") == _copilot_root().joinpath("agents", "__init__.py").read_text(
        encoding="utf-8"
    )
    assert agents_dir.joinpath("deepResearch.agent.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "agents", "deepResearch.agent.md"
    ).read_text(encoding="utf-8")
    assert prompts_dir.joinpath("__init__.prompt.md").read_text(encoding="utf-8") == _copilot_root().joinpath("prompts", "__init__.py").read_text(
        encoding="utf-8"
    )
    assert prompts_dir.joinpath("pyright_fix.prompt.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "prompts", "pyright_fix.md"
    ).read_text(encoding="utf-8")
    assert prompts_dir.joinpath("research-report-skeleton.prompt.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "prompts", "research-report-skeleton.prompt.md"
    ).read_text(encoding="utf-8")
    assert not tmp_path.joinpath(".github", "instructions").exists()


def test_build_configuration_writes_instruction_assets_and_generic_instructions(tmp_path: Path) -> None:
    build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=True)

    instructions_dir = tmp_path.joinpath(".github", "instructions")

    assert sorted(path.name for path in instructions_dir.iterdir()) == [
        "copilot-cli-security.instructions.md",
        "dev.instructions.md",
        "watch_exec.instructions.md",
    ]
    assert instructions_dir.joinpath("dev.instructions.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "instructions", "python", "dev.instructions.md"
    ).read_text(encoding="utf-8")
    assert instructions_dir.joinpath("watch_exec.instructions.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "instructions", "python", "watch_exec.prompt.md"
    ).read_text(encoding="utf-8")
    assert instructions_dir.joinpath("copilot-cli-security.instructions.md").read_text(encoding="utf-8") == _copilot_root().joinpath(
        "privacy.md"
    ).read_text(encoding="utf-8")
    assert tmp_path.joinpath(".github", "copilot-instructions.md").read_text(encoding="utf-8") == get_generic_instructions_path().read_text(
        encoding="utf-8"
    )
    assert not tmp_path.joinpath(".github", "agents").exists()
    assert not tmp_path.joinpath(".github", "prompts").exists()
