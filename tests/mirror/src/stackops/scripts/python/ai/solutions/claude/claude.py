

import json
from pathlib import Path

import pytest

from stackops.scripts.python.ai.solutions.claude import claude as claude_module


def test_build_configuration_writes_project_and_private_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("claude rules\n", encoding="utf-8")
    gitignore_calls: list[tuple[Path, bool, list[str]]] = []

    def fake_adjust_gitignore(*, repo_root: Path, include_default_entries: bool, extra_entries: list[str]) -> None:
        gitignore_calls.append((repo_root, include_default_entries, extra_entries.copy()))

    monkeypatch.setattr(claude_module, "get_generic_instructions_path", lambda: instructions_path)
    monkeypatch.setattr(claude_module.generic, "adjust_gitignore", fake_adjust_gitignore)

    claude_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=True)

    assert (repo_root / "CLAUDE.md").read_text(encoding="utf-8") == "claude rules\n"
    assert (repo_root / ".claude" / "settings.json").read_text(encoding="utf-8") == (
        json.dumps(
            {
                "$schema": claude_module.SETTINGS_SCHEMA_URL,
                "respectGitignore": True,
                "permissions": {
                    "deny": [
                        "Read(./.env)",
                        "Read(./.env.*)",
                        "Read(./secrets/**)",
                        "Read(./config/credentials.json)",
                        "Bash(curl *)",
                        "Bash(wget *)",
                    ]
                },
                "enableAllProjectMcpServers": False,
            },
            indent=2,
        )
        + "\n"
    )
    assert (repo_root / ".claude" / "settings.local.json").read_text(encoding="utf-8") == (
        json.dumps(
            {
                "$schema": claude_module.SETTINGS_SCHEMA_URL,
                "env": {
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
                    "CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY": "1",
                    "DISABLE_TELEMETRY": "1",
                    "DISABLE_ERROR_REPORTING": "1",
                    "DISABLE_BUG_COMMAND": "1",
                },
            },
            indent=2,
        )
        + "\n"
    )
    assert (repo_root / ".mcp.json").read_text(encoding="utf-8") == (json.dumps({"mcpServers": {}}, indent=2) + "\n")
    assert (repo_root / "CLAUDE.local.md").read_text(encoding="utf-8").startswith("# Local Claude Code preferences")
    assert (repo_root / ".gitignore").is_file()
    assert gitignore_calls == [(repo_root, False, [".claude/settings.local.json", "CLAUDE.local.md"])]


def test_build_configuration_preserves_existing_private_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    claude_dir = repo_root / ".claude"
    claude_dir.mkdir()
    settings_path = claude_dir / "settings.json"
    settings_local_path = claude_dir / "settings.local.json"
    mcp_path = repo_root / ".mcp.json"
    claude_local_path = repo_root / "CLAUDE.local.md"
    settings_path.write_text("shared sentinel\n", encoding="utf-8")
    settings_local_path.write_text("local sentinel\n", encoding="utf-8")
    mcp_path.write_text("mcp sentinel\n", encoding="utf-8")
    claude_local_path.write_text("claude local sentinel\n", encoding="utf-8")

    instructions_path = tmp_path / "instructions.md"
    instructions_path.write_text("unused\n", encoding="utf-8")

    def fake_adjust_gitignore(*, repo_root: Path, include_default_entries: bool, extra_entries: list[str]) -> None:
        _ = repo_root
        _ = include_default_entries
        _ = extra_entries

    monkeypatch.setattr(claude_module, "get_generic_instructions_path", lambda: instructions_path)
    monkeypatch.setattr(claude_module.generic, "adjust_gitignore", fake_adjust_gitignore)

    claude_module.build_configuration(repo_root=repo_root, add_private_config=True, add_instructions=False)

    assert settings_path.read_text(encoding="utf-8") == "shared sentinel\n"
    assert settings_local_path.read_text(encoding="utf-8") == "local sentinel\n"
    assert mcp_path.read_text(encoding="utf-8") == "mcp sentinel\n"
    assert claude_local_path.read_text(encoding="utf-8") == "claude local sentinel\n"
    assert (repo_root / "CLAUDE.md").exists() is False
    assert (repo_root / ".gitignore").is_file()
