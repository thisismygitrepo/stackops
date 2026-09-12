from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_fire_command import fire_jobs_environment, fire_jobs_impl
from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_args_helper import FireJobArgs
from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_environment import FireEnvironment, build_uv_run_shell_prefix


@pytest.mark.parametrize("cmd", [False, True])
def test_windows_environment_prefix_uses_selected_shell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, cmd: bool) -> None:
    project = tmp_path / "owner ' folder"
    environment = FireEnvironment(project_root=project, directory=project / ".venv", interpreter=project / ".venv/Scripts/python.exe")
    with monkeypatch.context() as patch:
        patch.setattr(fire_jobs_environment.os, "name", "nt")
        prefix = build_uv_run_shell_prefix(environment=environment, frozen=False, cmd=cmd)
    assert "--no-sync" in prefix
    assert "--no-active" in prefix
    if cmd:
        assert prefix.startswith(f"""set "UV_PROJECT_ENVIRONMENT={environment.directory}" && uv run """)
        command = fire_jobs_impl._apply_command_modifiers(
            args=FireJobArgs(cmd=True), command=prefix + " python script.py", choice_file=project / "script.py", repo_root=project
        )
        assert command == "start cmd -Argument '/k " + (prefix + " python script.py").replace("'", "''") + "'"
    else:
        environment_value = str(environment.directory).replace("'", "''")
        assert prefix.startswith(f"""$env:UV_PROJECT_ENVIRONMENT = '{environment_value}'; & 'uv' 'run' """)


@pytest.mark.parametrize("cmd", [False, True])
def test_windows_standalone_script_clears_inherited_project_environment(monkeypatch: pytest.MonkeyPatch, cmd: bool) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(fire_jobs_environment.os, "name", "nt")
        prefix = build_uv_run_shell_prefix(environment=None, frozen=False, cmd=cmd)
    assert "--no-project" in prefix
    if cmd:
        assert prefix.startswith('set "UV_PROJECT_ENVIRONMENT=" && uv run ')
    else:
        assert prefix.startswith("$env:UV_PROJECT_ENVIRONMENT = $null; & 'uv' 'run' ")
