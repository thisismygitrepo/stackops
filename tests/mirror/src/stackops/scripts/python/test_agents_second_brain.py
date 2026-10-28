from importlib.resources import files
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.agents_second_brain import configure_second_brain


INSTRUCTIONS_TEXT = files("stackops.scripts.python").joinpath("agents_second_brain.instructions.md").read_text(encoding="utf-8")


def test_init_installs_bundled_instructions(tmp_path: Path) -> None:
    instructions_path, action = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT, overwrite=False)

    assert instructions_path == tmp_path.joinpath("code", "agents", "second-brain", "AGENTS.md")
    assert action == "created"
    assert instructions_path.read_text(encoding="utf-8") == INSTRUCTIONS_TEXT


def test_init_preserves_existing_instructions_without_overwrite(tmp_path: Path) -> None:
    instructions_path = tmp_path.joinpath("code", "agents", "second-brain", "AGENTS.md")
    instructions_path.parent.mkdir(parents=True)
    instructions_path.write_text("keep this", encoding="utf-8")

    configured_instructions_path, action = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT, overwrite=False)

    assert configured_instructions_path == instructions_path
    assert action == "kept"
    assert instructions_path.read_text(encoding="utf-8") == "keep this"


def test_init_replaces_existing_instructions_with_overwrite(tmp_path: Path) -> None:
    instructions_path = tmp_path.joinpath("code", "agents", "second-brain", "AGENTS.md")
    instructions_path.parent.mkdir(parents=True)
    instructions_path.write_text("discard this", encoding="utf-8")

    configured_instructions_path, action = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT, overwrite=True)

    assert configured_instructions_path == instructions_path
    assert action == "overwritten"
    assert instructions_path.read_text(encoding="utf-8") == INSTRUCTIONS_TEXT


def test_init_adds_instructions_to_existing_second_brain(tmp_path: Path) -> None:
    second_brain_path = tmp_path.joinpath("code", "agents", "second-brain")
    existing_file = second_brain_path.joinpath("keep.md")
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("keep this", encoding="utf-8")

    instructions_path, action = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT, overwrite=False)

    assert action == "created"
    assert existing_file.read_text(encoding="utf-8") == "keep this"
    assert instructions_path.read_text(encoding="utf-8") == INSTRUCTIONS_TEXT


def test_init_refuses_to_replace_existing_configuration_file(tmp_path: Path) -> None:
    second_brain_path = tmp_path.joinpath("code", "agents", "second-brain")
    second_brain_path.parent.mkdir(parents=True)
    second_brain_path.write_text("keep this", encoding="utf-8")

    with pytest.raises(FileExistsError):
        configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT, overwrite=False)

    assert second_brain_path.read_text(encoding="utf-8") == "keep this"


def test_init_help_exposes_alias_and_overwrite_option() -> None:
    result = CliRunner().invoke(agents.get_app(), ["second-brain", "init", "--help"], terminal_width=120)
    alias_result = CliRunner().invoke(agents.get_app(), ["second-brain", "c", "--help"], terminal_width=120)

    assert result.exit_code == 0, result.output
    assert alias_result.exit_code == 0, alias_result.output
    assert "--overwrite" in result.output
    assert "--overwrite" in alias_result.output
