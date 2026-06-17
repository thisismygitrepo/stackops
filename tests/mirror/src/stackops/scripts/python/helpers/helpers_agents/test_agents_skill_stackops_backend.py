from pathlib import Path

import pytest
from rich.console import Console

from stackops.scripts.python.helpers.helpers_agents import agents_skill_stackops_backend as backend


def _write_skill(source_root: Path, skill_name: str, skill_text: str) -> Path:
    skill_path = source_root / skill_name
    skill_path.mkdir(parents=True, exist_ok=True)
    skill_path.joinpath("SKILL.md").write_text(skill_text, encoding="utf-8")
    return skill_path


def test_stackops_backend_copies_bundled_skill_to_repo_agents_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_root = tmp_path / "source-skills"
    source_path = _write_skill(source_root, "stackops", "---\nname: stackops\n---\n")
    source_path.joinpath("references").mkdir()
    source_path.joinpath("references", "source-map.md").write_text("source map\n", encoding="utf-8")

    repo_root = tmp_path / "repo"
    install_root = repo_root / "nested"
    install_root.mkdir(parents=True)
    monkeypatch.setattr(backend, "get_repo_root", lambda path: repo_root)

    results = backend.install_stackops_agent_skills(
        skill_names=("stackops",),
        skill_folder_names={"stackops": "stackops"},
        install_root=install_root,
        scope="local",
        source_root=source_root,
    )

    target_path = repo_root / ".agents" / "skills" / "stackops"
    assert target_path.joinpath("SKILL.md").read_text(encoding="utf-8") == "---\nname: stackops\n---\n"
    assert target_path.joinpath("references", "source-map.md").read_text(encoding="utf-8") == "source map\n"
    assert results == (
        backend.StackopsAgentSkillInstallResult(skill_name="stackops", source_path=source_path.resolve(), target_path=target_path),
    )


def test_stackops_backend_rejects_unbundled_alias(tmp_path: Path) -> None:
    source_root = tmp_path / "source-skills"
    _write_skill(source_root, "stackops", "---\nname: stackops\n---\n")

    with pytest.raises(ValueError, match="not bundled with the StackOps backend"):
        backend.install_stackops_agent_skills(
            skill_names=("agent-skills",),
            skill_folder_names={"agent-skills": "agent-skills"},
            install_root=tmp_path,
            scope="local",
            source_root=source_root,
        )


def test_stackops_backend_rejects_global_scope(tmp_path: Path) -> None:
    source_root = tmp_path / "source-skills"
    _write_skill(source_root, "stackops", "---\nname: stackops\n---\n")

    with pytest.raises(ValueError, match="only supports --scope local"):
        backend.install_stackops_agent_skills(
            skill_names=("stackops",),
            skill_folder_names={"stackops": "stackops"},
            install_root=tmp_path,
            scope="global",
            source_root=source_root,
        )


def test_stackops_backend_summary_prints_copied_paths() -> None:
    result = backend.StackopsAgentSkillInstallResult(
        skill_name="stackops",
        source_path=Path("/source-skills/stackops"),
        target_path=Path("/repo/.agents/skills/stackops"),
    )
    console = Console(record=True, force_terminal=False, width=120)

    backend.print_stackops_agent_skill_install_summary(results=(result,), console=console)

    output = console.export_text()
    assert "StackOps Skill Install" in output
    assert "stackops" in output
    assert str(result.source_path) in output
    assert str(result.target_path) in output
    assert "copied" in output
