from pathlib import Path

from git.repo import Repo

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_workspace import collect_workspace_resources
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext


def _context(*, home: Path, project_root: Path, working_directory: Path) -> DoctorContext:
    relative_parts = working_directory.relative_to(project_root).parts
    return DoctorContext(
        working_directory=working_directory, project_root=project_root,
        ancestor_directories=tuple(project_root.joinpath(*relative_parts[:count]) for count in range(len(relative_parts) + 1)),
        home_directory=home, xdg_config_directory=home / ".config", xdg_data_directory=home / ".local/share",
        codex_home=home / ".codex", pi_home=home / ".pi/agent", omp_home=home / ".omp/agent", claude_home=home / ".claude",
    )


def test_container_directory_without_a_valid_repository_still_resets_its_own_ai_folder(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    container = tmp_path / "container"
    (container / ".git" / "info").mkdir(parents=True)
    (container / ".ai").mkdir()
    Repo.init(container / "child")
    (container / "child" / ".ai").mkdir()
    (container / "plain" / ".ai").mkdir(parents=True)
    inventory = collect_workspace_resources(context=_context(home=home, project_root=container, working_directory=container), recursive=False)
    assert {entry.path for entry in inventory.entries} == {container / ".ai", container / "child" / ".ai"}
    assert inventory.diagnostics == ()


def test_running_from_a_repository_subdirectory_finds_the_repository_ai_folder(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    repository = tmp_path / "repo"
    Repo.init(repository)
    (repository / ".ai").mkdir()
    (repository / "pkg" / "inner").mkdir(parents=True)
    (repository / "pkg" / "inner" / ".ai").mkdir()
    inventory = collect_workspace_resources(
        context=_context(home=home, project_root=repository, working_directory=repository / "pkg"), recursive=False,
    )
    assert {entry.path for entry in inventory.entries} == {repository / ".ai"}
