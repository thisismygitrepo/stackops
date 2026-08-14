from importlib.resources import files
from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python import agents
from stackops.scripts.python.agents_second_brain import configure_second_brain


INSTRUCTIONS_TEXT = files("stackops.scripts.python").joinpath("agents_second_brain.instructions.md").read_text(encoding="utf-8")


def test_config_installs_bundled_instructions(tmp_path: Path) -> None:
    instructions_path = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert instructions_path == tmp_path.joinpath("code", "agents", "second-brain", "AGENTS.md")
    assert instructions_path.read_text(encoding="utf-8") == INSTRUCTIONS_TEXT


def test_config_preserves_existing_instructions(tmp_path: Path) -> None:
    instructions_path = tmp_path.joinpath("code", "agents", "second-brain", "AGENTS.md")
    instructions_path.parent.mkdir(parents=True)
    instructions_path.write_text("keep this", encoding="utf-8")

    configured_instructions_path = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert configured_instructions_path == instructions_path
    assert instructions_path.read_text(encoding="utf-8") == "keep this"


def test_config_adds_instructions_to_existing_second_brain(tmp_path: Path) -> None:
    second_brain_path = tmp_path.joinpath("code", "agents", "second-brain")
    existing_file = second_brain_path.joinpath("keep.md")
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("keep this", encoding="utf-8")

    instructions_path = configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert existing_file.read_text(encoding="utf-8") == "keep this"
    assert instructions_path.read_text(encoding="utf-8") == INSTRUCTIONS_TEXT


def test_config_refuses_to_replace_existing_configuration_file(tmp_path: Path) -> None:
    second_brain_path = tmp_path.joinpath("code", "agents", "second-brain")
    second_brain_path.parent.mkdir(parents=True)
    second_brain_path.write_text("keep this", encoding="utf-8")

    with pytest.raises(FileExistsError):
        configure_second_brain(home=tmp_path, instructions_text=INSTRUCTIONS_TEXT)

    assert second_brain_path.read_text(encoding="utf-8") == "keep this"


def test_config_help_exposes_alias_and_no_destructive_option() -> None:
    result = CliRunner().invoke(agents.get_app(), ["second-brain", "config", "--help"], terminal_width=120)
    alias_result = CliRunner().invoke(agents.get_app(), ["second-brain", "c", "--help"], terminal_width=120)

    assert result.exit_code == 0, result.output
    assert alias_result.exit_code == 0, alias_result.output
    assert "--overwrite" not in result.output
