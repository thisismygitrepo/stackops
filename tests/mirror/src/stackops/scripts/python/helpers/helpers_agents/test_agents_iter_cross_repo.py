import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_service, agents_iter_workspace_records
from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import HERDR_PROTOCOL, HERDR_VERSION
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrAgent,
    HerdrPane,
    HerdrSnapshot,
    HerdrTab,
    HerdrWorkspace,
    PaneId,
    TabId,
    TerminalId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import RECORD_SCHEMA_VERSION


def _build_workspace_snapshot(*, repo_root: Path, workspace_id: WorkspaceId, workspace_label: str, number: int) -> HerdrSnapshot:
    source_tab = HerdrTab(
        tab_id=TabId(f"{workspace_id}:t1"),
        workspace_id=workspace_id,
        label=f"{workspace_label}-001",
        number=1,
        agent_status="done",
        focused=False,
        pane_count=1,
    )
    successor_tab = HerdrTab(
        tab_id=TabId(f"{workspace_id}:t2"),
        workspace_id=workspace_id,
        label=f"{workspace_label}-002",
        number=2,
        agent_status="idle",
        focused=True,
        pane_count=1,
    )
    source_pane = HerdrPane(
        pane_id=PaneId(f"{workspace_id}:p1"),
        terminal_id=TerminalId(f"{workspace_id}:term1"),
        workspace_id=workspace_id,
        tab_id=source_tab.tab_id,
        agent_status="done",
        revision=20,
    )
    successor_pane = HerdrPane(
        pane_id=PaneId(f"{workspace_id}:p2"),
        terminal_id=TerminalId(f"{workspace_id}:term2"),
        workspace_id=workspace_id,
        tab_id=successor_tab.tab_id,
        agent_status="idle",
        revision=20,
    )
    source_cwd = repo_root.joinpath("nested", "agents", "source")
    successor_cwd = repo_root.joinpath("nested", "agents", "successor")
    source_cwd.mkdir(parents=True)
    successor_cwd.mkdir(parents=True)
    source_agent = HerdrAgent(
        terminal_id=source_pane.terminal_id,
        agent="codex",
        agent_status="done",
        workspace_id=workspace_id,
        tab_id=source_tab.tab_id,
        pane_id=source_pane.pane_id,
        cwd=str(source_cwd),
        foreground_cwd=str(source_cwd),
        focused=False,
        name=source_tab.label,
        display_agent=None,
        revision=20,
    )
    successor_agent = HerdrAgent(
        terminal_id=successor_pane.terminal_id,
        agent="codex",
        agent_status="idle",
        workspace_id=workspace_id,
        tab_id=successor_tab.tab_id,
        pane_id=successor_pane.pane_id,
        cwd=str(successor_cwd),
        foreground_cwd=str(successor_cwd),
        focused=True,
        name=successor_tab.label,
        display_agent=None,
        revision=20,
    )
    workspace = HerdrWorkspace(
        workspace_id=workspace_id,
        label=workspace_label,
        number=number,
        active_tab_id=successor_tab.tab_id,
        agent_status="idle",
        focused=number == 1,
        pane_count=2,
        tab_count=2,
    )
    return HerdrSnapshot(
        workspaces=(workspace,), tabs=(source_tab, successor_tab), panes=(source_pane, successor_pane), agents=(source_agent, successor_agent)
    )


def _write_iteration_records(*, repo_root: Path, snapshot: HerdrSnapshot) -> None:
    workspace = snapshot.workspaces[0]
    source_tab, successor_tab = snapshot.tabs
    successor_pane = snapshot.panes[1]
    successor_agent = snapshot.agents[1]
    successor_agent_name = successor_agent.name
    assert successor_agent_name is not None
    run_path = repo_root.joinpath(".ai", "agentops", "iterations", workspace.label.removeprefix("iter-"))
    iteration_path = run_path.joinpath("iter-001")
    iteration_path.mkdir(parents=True)
    run_path.joinpath("run.json").write_text(
        json.dumps(
            {
                "schema_version": RECORD_SCHEMA_VERSION,
                "herdr_version": HERDR_VERSION,
                "herdr_protocol": HERDR_PROTOCOL,
                "herdr_session": "default",
                "workspace_id": workspace.workspace_id,
                "workspace_label": workspace.label,
            }
        ),
        encoding="utf-8",
    )
    iteration_path.joinpath("handoff.json").write_text(
        json.dumps(
            {
                "schema_version": RECORD_SCHEMA_VERSION,
                "herdr_version": HERDR_VERSION,
                "herdr_protocol": HERDR_PROTOCOL,
                "herdr_session": "default",
                "workspace_id": workspace.workspace_id,
                "source_iteration": 1,
                "source_tab_id": source_tab.tab_id,
                "successor_iteration": 2,
                "successor_tab_id": successor_tab.tab_id,
                "successor_pane_id": successor_pane.pane_id,
                "successor_terminal_id": successor_pane.terminal_id,
                "successor_agent_name": successor_agent_name,
                "accepted_revision": 10,
            }
        ),
        encoding="utf-8",
    )


def test_status_and_close_resolve_each_workspace_repository_from_herdr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERDR_SESSION", raising=False)
    repo_alpha = tmp_path.joinpath("repo-alpha")
    repo_beta = tmp_path.joinpath("repo-beta")
    alpha_snapshot = _build_workspace_snapshot(
        repo_root=repo_alpha, workspace_id=WorkspaceId("workspace-alpha"), workspace_label="iter-alpha", number=1
    )
    beta_snapshot = _build_workspace_snapshot(repo_root=repo_beta, workspace_id=WorkspaceId("workspace-beta"), workspace_label="iter-beta", number=2)
    _write_iteration_records(repo_root=repo_alpha, snapshot=alpha_snapshot)
    _write_iteration_records(repo_root=repo_beta, snapshot=beta_snapshot)
    snapshot = HerdrSnapshot(
        workspaces=(*alpha_snapshot.workspaces, *beta_snapshot.workspaces),
        tabs=(*alpha_snapshot.tabs, *beta_snapshot.tabs),
        panes=(*alpha_snapshot.panes, *beta_snapshot.panes),
        agents=(*alpha_snapshot.agents, *beta_snapshot.agents),
    )
    outside_git = tmp_path.joinpath("outside-git")
    outside_git.mkdir()
    monkeypatch.chdir(outside_git)

    def repo_root_for_agent_path(path: Path) -> Path | None:
        resolved_path = path.resolve(strict=True)
        for repo_root in (repo_alpha, repo_beta):
            if resolved_path.is_relative_to(repo_root):
                return repo_root
        return None

    def current_snapshot() -> HerdrSnapshot:
        return snapshot

    closed_tab_ids: list[TabId] = []

    def record_close(*, tab_id: TabId) -> None:
        closed_tab_ids.append(tab_id)

    monkeypatch.setattr(agents_iter_workspace_records, "get_repo_root", repo_root_for_agent_path)
    monkeypatch.setattr(agents_iter_service, "capture_herdr_snapshot", current_snapshot)
    monkeypatch.setattr(agents_iter_service, "close_tab", record_close)

    statuses = agents_iter_service.get_iter_workspace_statuses(workspace_id=None, retain_previous=0)

    assert tuple(status.plan.repo_root for status in statuses) == (repo_alpha, repo_beta)
    assert tuple(tuple(tab.tab_id for tab in status.plan.closable_tabs) for status in statuses) == (
        (TabId("workspace-alpha:t1"),),
        (TabId("workspace-beta:t1"),),
    )

    results = agents_iter_service.close_iter_workspace_plans(close_plans=tuple(status.plan for status in statuses), report=lambda _message: None)

    assert closed_tab_ids == [TabId("workspace-alpha:t1"), TabId("workspace-beta:t1")]
    assert tuple(tuple(tab.tab_id for tab in result.closed_tabs) for result in results) == (
        (TabId("workspace-alpha:t1"),),
        (TabId("workspace-beta:t1"),),
    )
    assert all(result.failed_tabs == () for result in results)
    assert all(result.skipped_tabs == () for result in results)
