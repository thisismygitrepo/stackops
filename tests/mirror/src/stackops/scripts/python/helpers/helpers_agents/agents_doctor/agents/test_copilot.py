from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.agents.copilot import collect
from stackops.scripts.python.helpers.helpers_agents.agents_doctor.models import DoctorContext


@pytest.fixture
def copilot_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DoctorContext:
    home = tmp_path / "home"
    project = tmp_path / "project"
    home.mkdir()
    project.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("COPILOT_HOME", raising=False)
    return DoctorContext(
        project,
        project,
        (project,),
        home,
        home / ".config",
        home / ".local/share",
        home / ".codex",
        home / ".pi/agent",
        home / ".omp/agent",
        home / ".claude",
    )


@pytest.mark.parametrize("relative_manifest", ["_direct/direct-plugin/plugin.json", "some-marketplace/marketplace-plugin/plugin.json"])
def test_collect_finds_plugins_under_installed_plugins(copilot_context: DoctorContext, relative_manifest: str) -> None:
    manifest = copilot_context.home_directory / ".copilot/installed-plugins" / relative_manifest
    manifest.parent.mkdir(parents=True)
    manifest.write_text("""{"name": "demo", "version": "0.1.0"}""", encoding="utf-8")
    plugin_paths = [resource.path for resource in collect(context=copilot_context) if resource.kind == "plugin"]
    assert plugin_paths == [manifest]


def test_collect_honors_copilot_home_for_plugins(copilot_context: DoctorContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    configured_home = tmp_path / "custom-copilot-home"
    monkeypatch.setenv("COPILOT_HOME", str(configured_home))
    manifest = configured_home / "installed-plugins/_direct/direct-plugin/plugin.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("""{"name": "demo", "version": "0.1.0"}""", encoding="utf-8")
    plugin_paths = [resource.path for resource in collect(context=copilot_context) if resource.kind == "plugin"]
    assert plugin_paths == [manifest]
