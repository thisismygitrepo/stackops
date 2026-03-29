from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from git import Actor, Repo

from machineconfig.scripts.python.helpers.helpers_repos import repo_analyzer_1


def _create_test_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path.joinpath("repo")
    repo_path.mkdir()

    repo = Repo.init(repo_path)
    python_file = repo_path.joinpath("demo.py")
    python_file.write_text("""print("hello")\n""", encoding="utf-8")

    repo.index.add(["demo.py"])
    actor = Actor("Test User", "test@example.com")
    repo.index.commit("init", author=actor, committer=actor)

    return repo_path.resolve()


def test_gitcs_viz_uses_flag_style_required_by_gitcs(tmp_path: Path) -> None:
    repo_path = _create_test_repo(tmp_path)

    with (
        patch("machineconfig.utils.installer_utils.installer_cli.install_if_missing") as install_if_missing,
        patch.object(repo_analyzer_1.subprocess, "run", return_value=CompletedProcess(args=["gitcs"], returncode=0, stdout="ok", stderr="")) as run,
    ):
        repo_analyzer_1.gitcs_viz(repo_path=repo_path, email="dev@example.com")

    install_if_missing.assert_called_once_with(which="gitcs", binary_name=None, verbose=True)
    assert run.call_count == 2

    first_call = run.call_args_list[0]
    command = first_call.args[0]

    assert command[0:3] == ["gitcs", "-path", str(repo_path)]
    assert "-since" in command
    assert "-until" in command
    assert "-email" in command
    assert "--since" not in command
    assert "--until" not in command
    assert "--email" not in command
    assert first_call.kwargs["cwd"] == str(repo_path)
    assert first_call.kwargs["capture_output"] is True
    assert first_call.kwargs["text"] is True
    assert "input" not in first_call.kwargs
