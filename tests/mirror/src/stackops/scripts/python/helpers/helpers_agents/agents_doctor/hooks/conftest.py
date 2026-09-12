from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks import codex_hooks
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext


@pytest.fixture
def hook_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DoctorContext:
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    home.mkdir()
    monkeypatch.setattr(codex_hooks, "CODEX_SYSTEM_ROOT", tmp_path / "system")
    for variable in ("OPENCODE_CONFIG", "OPENCODE_CONFIG_DIR", "XDG_DATA_HOME", "OMP_PROFILE"):
        monkeypatch.delenv(variable, raising=False)
    return DoctorContext(
        working_directory=project,
        project_root=project,
        ancestor_directories=(project,),
        home_directory=home,
        xdg_config_directory=home / ".config",
        xdg_data_directory=home / ".local" / "share",
        codex_home=home / ".codex",
        pi_home=home / ".pi" / "agent",
        omp_home=home / ".omp" / "agent",
        claude_home=home / ".claude",
    )
