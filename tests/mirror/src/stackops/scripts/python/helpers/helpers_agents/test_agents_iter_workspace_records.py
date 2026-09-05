import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_records, agents_iter_workspace_records
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrSnapshot,
    HerdrTab,
    HerdrWorkspace,
    PaneId,
    TabId,
    TerminalId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import RECORD_SCHEMA_VERSION


@pytest.fixture
def iter_workspace() -> HerdrWorkspace:
    return HerdrWorkspace(
        workspace_id=WorkspaceId("w1"),
        label="iter-alpha",
        number=1,
        active_tab_id=TabId("w1:t1"),
        agent_status="idle",
        focused=True,
        pane_count=2,
        tab_count=2,
    )


type SnapshotEntry = tuple[HerdrTab, HerdrAgent]


def _entry(*, workspace: HerdrWorkspace, number: int, label: str, cwd: str | None, foreground_cwd: str | None) -> SnapshotEntry:
    tab_id = TabId(f"{workspace.workspace_id}:t{number}")
    tab = HerdrTab(tab_id=tab_id, workspace_id=workspace.workspace_id, label=label, number=number, agent_status="idle", focused=False, pane_count=1)
    agent = HerdrAgent(
        terminal_id=TerminalId(f"term-{workspace.workspace_id}-{number}"),
        agent="codex",
        agent_status="idle",
        workspace_id=workspace.workspace_id,
        tab_id=tab_id,
        pane_id=PaneId(f"{workspace.workspace_id}:p{number}"),
        cwd=cwd,
        foreground_cwd=foreground_cwd,
        focused=False,
        name=f"agent-{workspace.workspace_id}-{number}",
        display_agent="Codex",
        revision=1,
    )
    return tab, agent


def _snapshot(*, workspaces: tuple[HerdrWorkspace, ...], entries: tuple[SnapshotEntry, ...]) -> HerdrSnapshot:
    return HerdrSnapshot(workspaces=workspaces, tabs=tuple(tab for tab, _agent in entries), panes=(), agents=tuple(agent for _tab, agent in entries))


def _write_run_manifest(*, project_root: Path, run_slug: str, herdr_session: str, workspace_id: str, workspace_label: str) -> Path:
    run_path = project_root.joinpath(".ai", "agentops", "iterations", run_slug)
    run_path.mkdir(parents=True)
    run_path.joinpath("run.json").write_text(
        json.dumps(
            {
                "schema_version": RECORD_SCHEMA_VERSION,
                "herdr_session": herdr_session,
                "workspace_id": workspace_id,
                "workspace_label": workspace_label,
            }
        ),
        encoding="utf-8",
    )
    return run_path


def test_multiple_managed_agent_subdirectories_resolve_one_non_git_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace
) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    project_root = tmp_path.joinpath("project")
    first_subdirectory = project_root.joinpath("services", "first")
    second_subdirectory = project_root.joinpath("services", "second")
    first_subdirectory.mkdir(parents=True)
    second_subdirectory.mkdir(parents=True)
    run_path = _write_run_manifest(
        project_root=project_root, run_slug="alpha", herdr_session="default", workspace_id="w1", workspace_label="iter-alpha"
    )
    first_entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(first_subdirectory), foreground_cwd=None)
    second_entry = _entry(workspace=iter_workspace, number=2, label="iter-alpha-002", cwd=None, foreground_cwd=str(second_subdirectory))
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(first_entry, second_entry))

    resolved = agents_iter_workspace_records.resolve_iter_workspace_run_path(snapshot=snapshot, workspace=iter_workspace)

    assert not project_root.joinpath(".git").exists()
    assert resolved == run_path


def test_other_workspace_and_unusable_paths_are_ignored_when_one_exact_run_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace
) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    project_root = tmp_path.joinpath("project")
    valid_subdirectory = project_root.joinpath("service")
    valid_subdirectory.mkdir(parents=True)
    run_path = _write_run_manifest(
        project_root=project_root, run_slug="alpha", herdr_session="default", workspace_id="w1", workspace_label="iter-alpha"
    )
    no_record_directory = tmp_path.joinpath("no-record")
    no_record_directory.mkdir()
    file_path = tmp_path.joinpath("not-a-directory")
    file_path.touch()
    missing_path = tmp_path.joinpath("missing")
    other_workspace_directory = tmp_path.joinpath("other-project")
    other_workspace_directory.mkdir()

    other_workspace = HerdrWorkspace(
        workspace_id=WorkspaceId("w2"),
        label="iter-beta",
        number=2,
        active_tab_id=TabId("w2:t1"),
        agent_status="idle",
        focused=False,
        pane_count=1,
        tab_count=1,
    )
    entries = (
        _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(valid_subdirectory), foreground_cwd="relative/path"),
        _entry(workspace=iter_workspace, number=2, label="iter-alpha-002", cwd=str(missing_path), foreground_cwd=str(file_path)),
        _entry(workspace=iter_workspace, number=3, label="iter-alpha-003", cwd=str(no_record_directory), foreground_cwd=None),
        _entry(workspace=iter_workspace, number=4, label="iter-alpha-tracker", cwd=str(other_workspace_directory), foreground_cwd=None),
        _entry(workspace=other_workspace, number=1, label="iter-beta-001", cwd=str(other_workspace_directory), foreground_cwd=None),
    )
    snapshot = _snapshot(workspaces=(iter_workspace, other_workspace), entries=entries)

    resolved = agents_iter_workspace_records.resolve_iter_workspace_run_path(snapshot=snapshot, workspace=iter_workspace)

    assert resolved == run_path


def test_no_exact_run_manifest_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    no_record_directory = tmp_path.joinpath("no-record")
    no_record_directory.mkdir()
    entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(no_record_directory), foreground_cwd="relative/path")
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(entry,))

    with pytest.raises(RuntimeError, match="Cannot locate AgentOps records for Herdr iter workspace") as error:
        agents_iter_workspace_records.resolve_iter_workspace_run_path(snapshot=snapshot, workspace=iter_workspace)

    assert str(no_record_directory) in str(error.value)
    assert "is not absolute" in str(error.value)


def test_multiple_exact_run_manifests_raise_ambiguity_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    first_project = tmp_path.joinpath("first-project")
    second_project = tmp_path.joinpath("second-project")
    first_subdirectory = first_project.joinpath("service")
    second_subdirectory = second_project.joinpath("service")
    first_subdirectory.mkdir(parents=True)
    second_subdirectory.mkdir(parents=True)
    first_run_path = _write_run_manifest(
        project_root=first_project, run_slug="alpha", herdr_session="default", workspace_id="w1", workspace_label="iter-alpha"
    )
    second_run_path = _write_run_manifest(
        project_root=second_project, run_slug="alpha", herdr_session="default", workspace_id="w1", workspace_label="iter-alpha"
    )
    first_entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(first_subdirectory), foreground_cwd=None)
    second_entry = _entry(workspace=iter_workspace, number=2, label="iter-alpha-002", cwd=str(second_subdirectory), foreground_cwd=None)
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(first_entry, second_entry))

    with pytest.raises(RuntimeError, match="resolves to multiple AgentOps runs") as error:
        agents_iter_workspace_records.resolve_iter_workspace_run_path(snapshot=snapshot, workspace=iter_workspace)

    assert str(first_run_path) in str(error.value)
    assert str(second_run_path) in str(error.value)


@pytest.mark.parametrize(
    ("herdr_session", "workspace_id", "workspace_label", "expected_error"),
    (
        ("other", "w1", "iter-alpha", "belongs to Herdr session"),
        ("default", "other", "iter-alpha", "workspace ID does not match"),
        ("default", "w1", "iter-beta", "label does not match"),
    ),
)
def test_run_manifest_must_exactly_match_live_workspace_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    iter_workspace: HerdrWorkspace,
    herdr_session: str,
    workspace_id: str,
    workspace_label: str,
    expected_error: str,
) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    project_root = tmp_path.joinpath("project")
    agent_directory = project_root.joinpath("service")
    agent_directory.mkdir(parents=True)
    _write_run_manifest(
        project_root=project_root, run_slug="alpha", herdr_session=herdr_session, workspace_id=workspace_id, workspace_label=workspace_label
    )
    entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(agent_directory), foreground_cwd=None)
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(entry,))

    with pytest.raises(RuntimeError, match=expected_error):
        agents_iter_workspace_records.resolve_iter_workspace_run_path(snapshot=snapshot, workspace=iter_workspace)


@pytest.mark.parametrize("workspace_label", ("iter-../escape", "iter-nested/run", "iter-windows\\run"))
def test_iter_workspace_slug_rejects_path_components(workspace_label: str) -> None:
    with pytest.raises(ValueError, match="one safe run slug"):
        agents_iter_records.parse_iter_workspace_slug(workspace_label=workspace_label)
