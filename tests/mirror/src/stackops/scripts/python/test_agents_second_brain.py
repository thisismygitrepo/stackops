import hashlib
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents


INSTRUCTIONS_SHA256 = "d62af7c89dfb154b7efa524eb755b20b3bfdd72785d70070099009e08db60e42"


def test_config_installs_bundled_instructions_and_symlink(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))

    result = CliRunner().invoke(agents.get_app(), ["second-brain", "config"])

    link_path = tmp_path.joinpath("code", "agents", "second-brain")
    target_path = tmp_path.joinpath("dotfiles", "stackops", "second-brain")
    instructions_path = target_path.joinpath("AGENTS.md")
    assert result.exit_code == 0, result.output
    assert link_path.is_symlink()
    assert link_path.readlink() == target_path
    assert hashlib.sha256(instructions_path.read_bytes()).hexdigest() == INSTRUCTIONS_SHA256
    assert link_path.joinpath("AGENTS.md").read_bytes() == instructions_path.read_bytes()


def test_config_refuses_existing_instructions_without_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    initial_result = runner.invoke(agents.get_app(), ["second-brain", "config"])
    instructions_path = tmp_path.joinpath("dotfiles", "stackops", "second-brain", "AGENTS.md")
    instructions_path.write_text("keep this", encoding="utf-8")

    result = runner.invoke(agents.get_app(), ["second-brain", "config"])

    assert initial_result.exit_code == 0, initial_result.output
    assert result.exit_code == 1
    assert isinstance(result.exception, FileExistsError)
    assert instructions_path.read_text(encoding="utf-8") == "keep this"


@pytest.mark.parametrize("overwrite_option", ["--overwrite", "-w"])
def test_config_overwrites_existing_instructions(overwrite_option: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    initial_result = runner.invoke(agents.get_app(), ["second-brain", "config"])
    instructions_path = tmp_path.joinpath("dotfiles", "stackops", "second-brain", "AGENTS.md")
    instructions_path.write_text("replace this", encoding="utf-8")

    result = runner.invoke(agents.get_app(), ["second-brain", "config", overwrite_option])

    assert initial_result.exit_code == 0, initial_result.output
    assert result.exit_code == 0, result.output
    assert hashlib.sha256(instructions_path.read_bytes()).hexdigest() == INSTRUCTIONS_SHA256


def test_config_overwrite_refuses_to_delete_second_brain_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    link_path = tmp_path.joinpath("code", "agents", "second-brain")
    existing_file = link_path.joinpath("keep.md")
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("keep this", encoding="utf-8")

    result = CliRunner().invoke(agents.get_app(), ["second-brain", "config", "--overwrite"])

    assert result.exit_code == 1
    assert isinstance(result.exception, IsADirectoryError)
    assert existing_file.read_text(encoding="utf-8") == "keep this"
    assert not tmp_path.joinpath("dotfiles").exists()


def test_config_overwrite_replaces_existing_configuration_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    link_path = tmp_path.joinpath("code", "agents", "second-brain")
    link_path.parent.mkdir(parents=True)
    link_path.write_text("replace this", encoding="utf-8")

    result = CliRunner().invoke(agents.get_app(), ["second-brain", "config", "--overwrite"])

    target_path = tmp_path.joinpath("dotfiles", "stackops", "second-brain")
    assert result.exit_code == 0, result.output
    assert link_path.is_symlink()
    assert link_path.readlink() == target_path
    assert hashlib.sha256(target_path.joinpath("AGENTS.md").read_bytes()).hexdigest() == INSTRUCTIONS_SHA256


def test_config_help_exposes_overwrite_aliases() -> None:
    result = CliRunner().invoke(agents.get_app(), ["second-brain", "config", "--help"], terminal_width=120)
    agents_config_result = CliRunner().invoke(agents.get_app(), ["add-config", "--help"], terminal_width=120)

    assert result.exit_code == 0, result.output
    assert agents_config_result.exit_code == 0, agents_config_result.output
    assert "--overwrite" in result.output
    assert "-w" in result.output
    assert "--overwrite" not in agents_config_result.output
