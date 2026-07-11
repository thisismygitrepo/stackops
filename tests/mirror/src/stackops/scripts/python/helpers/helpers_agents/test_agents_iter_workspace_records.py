from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_workspace_records
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


def test_multiple_managed_agent_subdirectories_resolve_one_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace
) -> None:
    repo_root = tmp_path.joinpath("repo")
    first_subdirectory = repo_root.joinpath("services", "first")
    second_subdirectory = repo_root.joinpath("services", "second")
    first_subdirectory.mkdir(parents=True)
    second_subdirectory.mkdir(parents=True)
    first_entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(first_subdirectory), foreground_cwd=None)
    second_entry = _entry(workspace=iter_workspace, number=2, label="iter-alpha-002", cwd=None, foreground_cwd=str(second_subdirectory))
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(first_entry, second_entry))
    observed_candidates: list[Path] = []

    def find_repo_root(candidate: Path) -> Path | None:
        observed_candidates.append(candidate)
        return repo_root

    monkeypatch.setattr(agents_iter_workspace_records, "get_repo_root", find_repo_root)

    resolved = agents_iter_workspace_records.resolve_iter_workspace_repo_root(snapshot=snapshot, workspace=iter_workspace)

    assert resolved == repo_root
    assert observed_candidates == [first_subdirectory, second_subdirectory]


def test_other_workspace_and_unusable_paths_are_ignored_when_one_root_is_valid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace
) -> None:
    repo_root = tmp_path.joinpath("repo")
    valid_subdirectory = repo_root.joinpath("service")
    valid_subdirectory.mkdir(parents=True)
    no_repo_directory = tmp_path.joinpath("no-repo")
    no_repo_directory.mkdir()
    file_path = tmp_path.joinpath("not-a-directory")
    file_path.touch()
    missing_path = tmp_path.joinpath("missing")
    other_workspace_directory = tmp_path.joinpath("other-repo")
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
        _entry(workspace=iter_workspace, number=3, label="iter-alpha-003", cwd=str(no_repo_directory), foreground_cwd=None),
        _entry(workspace=iter_workspace, number=4, label="iter-alpha-tracker", cwd=str(other_workspace_directory), foreground_cwd=None),
        _entry(workspace=other_workspace, number=1, label="iter-beta-001", cwd=str(other_workspace_directory), foreground_cwd=None),
    )
    snapshot = _snapshot(workspaces=(iter_workspace, other_workspace), entries=entries)
    observed_candidates: list[Path] = []

    def find_repo_root(candidate: Path) -> Path | None:
        observed_candidates.append(candidate)
        if candidate == valid_subdirectory:
            return repo_root
        if candidate == no_repo_directory:
            return None
        raise AssertionError(f"Unexpected repository lookup for {candidate}")

    monkeypatch.setattr(agents_iter_workspace_records, "get_repo_root", find_repo_root)

    resolved = agents_iter_workspace_records.resolve_iter_workspace_repo_root(snapshot=snapshot, workspace=iter_workspace)

    assert resolved == repo_root
    assert observed_candidates == [valid_subdirectory, no_repo_directory]


def test_zero_repo_roots_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace) -> None:
    no_repo_directory = tmp_path.joinpath("no-repo")
    no_repo_directory.mkdir()
    entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(no_repo_directory), foreground_cwd="relative/path")
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(entry,))

    def find_repo_root(candidate: Path) -> Path | None:
        assert candidate == no_repo_directory
        return None

    monkeypatch.setattr(agents_iter_workspace_records, "get_repo_root", find_repo_root)

    with pytest.raises(RuntimeError, match="Cannot resolve the Git repository for Herdr iter workspace") as error:
        agents_iter_workspace_records.resolve_iter_workspace_repo_root(snapshot=snapshot, workspace=iter_workspace)

    assert "is not in a Git repository" in str(error.value)
    assert "is not absolute" in str(error.value)


def test_multiple_repo_roots_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, iter_workspace: HerdrWorkspace) -> None:
    first_root = tmp_path.joinpath("first-repo")
    second_root = tmp_path.joinpath("second-repo")
    first_subdirectory = first_root.joinpath("service")
    second_subdirectory = second_root.joinpath("service")
    first_subdirectory.mkdir(parents=True)
    second_subdirectory.mkdir(parents=True)
    first_entry = _entry(workspace=iter_workspace, number=1, label="iter-alpha-001", cwd=str(first_subdirectory), foreground_cwd=None)
    second_entry = _entry(workspace=iter_workspace, number=2, label="iter-alpha-002", cwd=str(second_subdirectory), foreground_cwd=None)
    snapshot = _snapshot(workspaces=(iter_workspace,), entries=(first_entry, second_entry))
    roots_by_candidate = {first_subdirectory: first_root, second_subdirectory: second_root}

    def find_repo_root(candidate: Path) -> Path | None:
        return roots_by_candidate[candidate]

    monkeypatch.setattr(agents_iter_workspace_records, "get_repo_root", find_repo_root)

    with pytest.raises(RuntimeError, match="resolves to multiple Git repositories") as error:
        agents_iter_workspace_records.resolve_iter_workspace_repo_root(snapshot=snapshot, workspace=iter_workspace)

    assert str(first_root) in str(error.value)
    assert str(second_root) in str(error.value)
