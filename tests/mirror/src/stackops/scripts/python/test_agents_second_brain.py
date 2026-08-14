import hashlib
from importlib.resources import files
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.agents_second_brain import configure_second_brain


INSTRUCTIONS_SHA256 = "d62af7c89dfb154b7efa524eb755b20b3bfdd72785d70070099009e08db60e42"
INSTRUCTIONS_TEXT = files("stackops.scripts.python").joinpath("agents_second_brain.instructions.md").read_text(encoding="utf-8")


def test_config_installs_bundled_instructions_and_symlink(tmp_path: Path) -> None:
    instructions_path, link_path, target_path = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert link_path.is_symlink()
    assert link_path.readlink() == target_path
    assert hashlib.sha256(instructions_path.read_bytes()).hexdigest() == INSTRUCTIONS_SHA256
    assert link_path.joinpath("AGENTS.md").read_bytes() == instructions_path.read_bytes()


def test_config_preserves_existing_instructions(tmp_path: Path) -> None:
    instructions_path = tmp_path.joinpath("dotfiles", "stackops", "second-brain", "AGENTS.md")
    instructions_path.parent.mkdir(parents=True)
    instructions_path.write_text("keep this", encoding="utf-8")

    configured_instructions_path, link_path, target_path = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert configured_instructions_path == instructions_path
    assert instructions_path.read_text(encoding="utf-8") == "keep this"
    assert link_path.is_symlink()
    assert link_path.readlink() == target_path


def test_config_refuses_to_replace_second_brain_directory(tmp_path: Path) -> None:
    link_path = tmp_path.joinpath("code", "agents", "second-brain")
    existing_file = link_path.joinpath("keep.md")
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("keep this", encoding="utf-8")

    with pytest.raises(IsADirectoryError):
        configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert existing_file.read_text(encoding="utf-8") == "keep this"
    assert not tmp_path.joinpath("dotfiles").exists()


def test_config_refuses_to_replace_existing_configuration_file(tmp_path: Path) -> None:
    link_path = tmp_path.joinpath("code", "agents", "second-brain")
    link_path.parent.mkdir(parents=True)
    link_path.write_text("keep this", encoding="utf-8")

    with pytest.raises(FileExistsError):
        configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert link_path.read_text(encoding="utf-8") == "keep this"
    assert not tmp_path.joinpath("dotfiles").exists()


def test_config_refuses_to_replace_wrong_symlink(tmp_path: Path) -> None:
    link_path = tmp_path.joinpath("code", "agents", "second-brain")
    unexpected_target = tmp_path.joinpath("unexpected-target")
    link_path.parent.mkdir(parents=True)
    unexpected_target.mkdir()
    link_path.symlink_to(unexpected_target, target_is_directory=True)

    with pytest.raises(FileExistsError):
        configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert link_path.is_symlink()
    assert link_path.readlink() == unexpected_target
    assert not tmp_path.joinpath("dotfiles").exists()


def test_config_help_exposes_no_destructive_option() -> None:
    result = CliRunner().invoke(agents.get_app(), ["second-brain", "config", "--help"], terminal_width=120)

    assert result.exit_code == 0, result.output
    assert "--overwrite" not in result.output
