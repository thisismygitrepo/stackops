

import subprocess
from pathlib import Path

import pytest

import stackops.scripts.python.helpers.helpers_agents.agents_run_context as run_context_module


def test_ensure_prompts_yaml_exists_writes_template_and_is_idempotent(tmp_path: Path) -> None:
    yaml_path = tmp_path / "prompts.yaml"

    created = run_context_module.ensure_prompts_yaml_exists(yaml_path)
    created_again = run_context_module.ensure_prompts_yaml_exists(yaml_path)

    assert created is True
    assert created_again is False
    assert "default: |" in yaml_path.read_text(encoding="utf-8")


def test_resolve_named_prompts_yaml_entry_formats_nested_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml_path = tmp_path / "prompts.yaml"
    yaml_path.write_text("placeholder: true\n", encoding="utf-8")

    monkeypatch.setattr(
        "stackops.utils.files.read.read_yaml",
        lambda _path: {
            "team": {
                "backend": {
                    "prompt": "Build API",
                    "directory": "src/backend",
                    "temperature": 0.1,
                    "description": "ignored",
                }
            }
        },
    )

    result = run_context_module.resolve_named_prompts_yaml_entry(
        prompts_yaml_path=str(yaml_path),
        entry_name="team.backend",
        where="all",
        entry_label="Prompt name",
    )

    assert "Build API" in result
    assert "Working directory: `src/backend`" in result
    assert "Temperature: 0.1" in result
    assert "ignored" not in result


def test_edit_prompts_yaml_prefers_hx_and_raises_on_failed_exit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    yaml_path = tmp_path / "prompts.yaml"
    yaml_path.write_text("default: value\n", encoding="utf-8")
    commands: list[list[str]] = []

    monkeypatch.setattr(run_context_module.shutil, "which", lambda name: "/usr/bin/hx" if name == "hx" else None)

    def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(run_context_module.subprocess, "run", fake_run)
    run_context_module.edit_prompts_yaml(yaml_path)

    assert commands == [["/usr/bin/hx", str(yaml_path)]]

    monkeypatch.setattr(
        run_context_module.subprocess,
        "run",
        lambda args, check: subprocess.CompletedProcess(args=args, returncode=7),
    )
    with pytest.raises(RuntimeError, match="status code 7"):
        run_context_module.edit_prompts_yaml(yaml_path)
