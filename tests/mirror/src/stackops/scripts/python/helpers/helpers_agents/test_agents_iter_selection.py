import json
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agents_agentops_cache import AgentopsCacheCleanResult
from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import (
    HerdrTab,
    HerdrWorkspace,
    IterWorkspaceClosePlan,
    IterWorkspaceStatus,
    ProtectedTab,
    TabId,
    WorkspaceId,
)
from stackops.scripts.python.helpers.helpers_agents.agents_iter_selection import (
    build_iter_workspace_preview,
    choose_agentops_cache_workspace_id,
    choose_iter_workspace_id,
)
from stackops.utils.options_utils import tv_options


def _status() -> IterWorkspaceStatus:
    workspace_id = WorkspaceId("w1")
    close_tab = HerdrTab(TabId("w1:t1"), workspace_id, "iter-alpha-001", 1, "done", False, 1)
    retained_tab = HerdrTab(TabId("w1:t2"), workspace_id, "iter-alpha-002", 2, "idle", True, 1)
    protected_tab = HerdrTab(TabId("w1:t3"), workspace_id, "iter-alpha-notes", 3, "idle", False, 1)
    workspace = HerdrWorkspace(
        workspace_id=workspace_id,
        label="iter-alpha",
        number=4,
        active_tab_id=retained_tab.tab_id,
        agent_status="idle",
        focused=True,
        pane_count=3,
        tab_count=3,
    )
    plan = IterWorkspaceClosePlan(
        workspace=workspace,
        repo_root=Path("/repo"),
        tabs=(close_tab, retained_tab, protected_tab),
        retained_tabs=(retained_tab,),
        protected_tabs=(ProtectedTab(tab=protected_tab, reason="unmanaged"),),
        closable_tabs=(close_tab,),
        retain_previous=0,
    )
    return IterWorkspaceStatus(workspace=workspace, plan=plan, latest_iteration=2, latest_agent=None, latest_agent_tab=retained_tab)


def test_interactive_workspace_selection_uses_tv_preview_and_returns_stable_id(monkeypatch: pytest.MonkeyPatch) -> None:
    status = _status()
    captured_preview: dict[str, str] = {}

    def select_workspace(options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> str:
        assert extension == "md"
        assert multi is False
        assert preview_size_percent == ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
        captured_preview.update(options_to_preview_mapping)
        return "iter-alpha [w1]"

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", select_workspace)

    workspace_id = choose_iter_workspace_id(statuses=(status,))

    assert workspace_id == "w1"
    assert tuple(captured_preview) == ("iter-alpha [w1]",)
    preview = captured_preview["iter-alpha [w1]"]
    assert "Workspace ID: `w1`" in preview
    assert "Workspace status: `idle`" in preview
    assert "Close: `1`" in preview
    assert "Retain: `1`" in preview
    assert "Protect: `1` (unmanaged=1)" in preview
    assert "`iter-alpha-001`" in preview


def test_interactive_workspace_selection_cancellation_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def cancel_selection(options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> None:
        assert options_to_preview_mapping
        assert extension == "md"
        assert multi is False
        assert preview_size_percent == ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
        return None

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", cancel_selection)

    with pytest.raises(RuntimeError, match="selection was cancelled"):
        choose_iter_workspace_id(statuses=(_status(),))


def test_iter_workspace_preview_reports_live_plan() -> None:
    preview = build_iter_workspace_preview(status=_status())

    assert "Latest iteration: `002`" in preview
    assert "Latest agent status: `idle`" in preview
    assert "`iter-alpha-notes` (`w1:t3`) — unmanaged" in preview


def test_agentops_cache_selection_previews_inactive_run_action(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_path = tmp_path.joinpath(".ai", "agentops", "iterations", "alpha")
    run_path.mkdir(parents=True)
    run_path.joinpath("run.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "herdr_version": "0.7.3",
                "herdr_protocol": 16,
                "herdr_session": "default",
                "workspace_id": "w9",
                "workspace_label": "iter-alpha",
            }
        ),
        encoding="utf-8",
    )
    result = AgentopsCacheCleanResult(
        repo_root=tmp_path,
        iterations_path=run_path.parent,
        removed_runs=(run_path,),
        protected_runs=(),
        unmanaged_entries=(),
        removed_entries=2,
        dry_run=True,
    )
    captured_preview: dict[str, str] = {}

    def select_run(options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float) -> str:
        assert extension == "md"
        assert multi is False
        assert preview_size_percent == ITER_WORKSPACE_PREVIEW_SIZE_PERCENT
        captured_preview.update(options_to_preview_mapping)
        return "iter-alpha [w9]"

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", select_run)

    workspace_id = choose_agentops_cache_workspace_id(result=result)

    assert workspace_id == WorkspaceId("w9")
    preview = captured_preview["iter-alpha [w9]"]
    assert "Current state: `inactive`" in preview
    assert "Clean action: `remove`" in preview
    assert "Record path: `./.ai/agentops/iterations/alpha`" in preview


def test_agentops_cache_selection_requires_a_managed_run(tmp_path: Path) -> None:
    result = AgentopsCacheCleanResult(
        repo_root=tmp_path,
        iterations_path=tmp_path.joinpath(".ai", "agentops", "iterations"),
        removed_runs=(),
        protected_runs=(),
        unmanaged_entries=(),
        removed_entries=0,
        dry_run=True,
    )

    with pytest.raises(RuntimeError, match="No current AgentOps iteration runs"):
        choose_agentops_cache_workspace_id(result=result)
