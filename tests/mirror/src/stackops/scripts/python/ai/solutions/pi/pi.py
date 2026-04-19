import json
from pathlib import Path

import pytest

import stackops.scripts.python.ai.solutions.pi.pi as pi_module


def test_build_configuration_writes_pi_files_without_clobbering_agents_md(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("pi rules\n", encoding="utf-8")
    agents_path = tmp_path / "AGENTS.md"
    agents_path.write_text("existing rules\n", encoding="utf-8")

    monkeypatch.setattr(pi_module, "get_generic_instructions_path", lambda: instructions_path)

    pi_module.build_configuration(repo_root=tmp_path, add_private_config=True, add_instructions=True)

    settings = json.loads((tmp_path / ".pi" / "settings.json").read_text(encoding="utf-8"))
    mcp_config = json.loads((tmp_path / ".pi" / "mcp.json").read_text(encoding="utf-8"))

    assert agents_path.read_text(encoding="utf-8") == "existing rules\n"
    assert settings == {"enableInstallTelemetry": False}
    assert mcp_config == {"mcpServers": {}}


def test_build_configuration_creates_agents_md_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("pi rules\n", encoding="utf-8")

    monkeypatch.setattr(pi_module, "get_generic_instructions_path", lambda: instructions_path)

    pi_module.build_configuration(repo_root=tmp_path, add_private_config=False, add_instructions=True)

    assert tmp_path.joinpath("AGENTS.md").read_text(encoding="utf-8") == "pi rules\n"
