import tomllib
from collections.abc import Callable
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from stackops.scripts.python import agents, cloud, devops, fire_jobs, seek, stackops_entry, terminal, utils
from stackops.utils.source_of_truth import REPO_ROOT


def test_skill_flag_prints_the_folder_then_the_guide() -> None:
    result = CliRunner().invoke(stackops_entry.get_app(), ["--skill"])
    assert result.exit_code == 0
    folder_line, _, guide = result.stdout.partition("\n")
    folder = Path(folder_line.removeprefix("Skill folder: "))
    assert folder.joinpath("references", "change-guide.md").is_file()
    assert guide.strip() == folder.joinpath("SKILL.md").read_text(encoding="utf-8").strip()


def test_wheel_ships_the_folder_the_skill_flag_reads() -> None:
    pyproject = tomllib.loads(REPO_ROOT.joinpath("pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"] == {"skills": "stackops/skills"}
    assert REPO_ROOT.joinpath("skills", "stackops", "SKILL.md").is_file()


@pytest.mark.parametrize("get_app", [agents.get_app, cloud.get_app, devops.get_app, fire_jobs.get_app, seek.get_app, terminal.get_app, utils.get_app])
def test_entrypoint_help_points_agents_to_the_skill(get_app: Callable[[], typer.Typer]) -> None:
    result = CliRunner().invoke(get_app(), ["--help"])
    assert result.exit_code == 0
    assert "stackops --skill" in result.stdout
