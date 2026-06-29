import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_impl


def test_close_iter_workspaces_keeps_latest_and_three_previous_iter_tabs(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    reports: list[str] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t5","agent_status":"working","focused":false,"pane_count":5,"tab_count":5},
{"workspace_id":"w2","label":"main","number":2,"active_tab_id":"w2:t1","agent_status":"idle","focused":false,"pane_count":1,"tab_count":1},
{"workspace_id":"w3","label":"iter-beta","number":3,"active_tab_id":"w3:t2","agent_status":"done","focused":false,"pane_count":2,"tab_count":2}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"iter-alpha-002","number":2,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"iter-alpha-004","number":3,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"iter-alpha-005","number":4,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t5","workspace_id":"w1","label":"iter-alpha-006","number":5,"agent_status":"working","focused":true,"pane_count":1},
{"tab_id":"w2:t1","workspace_id":"w2","label":"main","number":1,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w3:t1","workspace_id":"w3","label":"iter-beta-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w3:t2","workspace_id":"w3","label":"iter-beta-002","number":2,"agent_status":"done","focused":false,"pane_count":1}
]}}
"""
            case ["herdr", "pane", "list"]:
                return """
{"result":{"panes":[
{"pane_id":"w1:p1","workspace_id":"w1","tab_id":"w1:t1","agent_status":"done"},
{"pane_id":"w1:p2","workspace_id":"w1","tab_id":"w1:t2","agent_status":"idle"},
{"pane_id":"w1:p3","workspace_id":"w1","tab_id":"w1:t3","agent_status":"idle"},
{"pane_id":"w1:p4","workspace_id":"w1","tab_id":"w1:t4","agent_status":"idle"},
{"pane_id":"w1:p5","workspace_id":"w1","tab_id":"w1:t5","agent_status":"working"},
{"pane_id":"w2:p1","workspace_id":"w2","tab_id":"w2:t1","agent_status":"idle"},
{"pane_id":"w3:p1","workspace_id":"w3","tab_id":"w3:t1","agent_status":"done"},
{"pane_id":"w3:p2","workspace_id":"w3","tab_id":"w3:t2","agent_status":"done"}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[]}}
"""
            case ["herdr", "tab", "close", _tab_id]:
                return ""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    summaries = agents_iter_impl.close_iter_workspaces(
        workspace_name=None,
        all_workspaces=True,
        close_n_old_iters=3,
        report=reports.append,
    )

    assert [command for command in commands if command[:3] == ["herdr", "tab", "close"]] == [
        ["herdr", "tab", "close", "w1:t1"],
        ["herdr", "tab", "close", "w1:t2"],
    ]
    assert [summary.workspace.label for summary in summaries] == ["iter-alpha", "iter-beta"]
    assert [tab.label for tab in summaries[0].kept_tabs] == ["iter-alpha-004", "iter-alpha-005", "iter-alpha-006"]
    assert len(summaries[1].closed_tabs) == 0
    assert "Planning iter close: 2 workspace(s), 7 tab(s), closing 2" in reports[0]
    assert "Closing 1/2: iter-alpha tab #1 iter-alpha-001 [done] w1:t1" in reports
    assert "Closing 2/2: iter-alpha tab #2 iter-alpha-002 [idle] w1:t2" in reports


def test_close_iter_workspaces_keeps_next_tab_after_running_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t3","agent_status":"working","focused":false,"pane_count":7,"tab_count":7}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"iter-alpha-002","number":2,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"iter-alpha-003","number":3,"agent_status":"working","focused":true,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"iter-alpha-004","number":4,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t5","workspace_id":"w1","label":"iter-alpha-005","number":5,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t6","workspace_id":"w1","label":"iter-alpha-006","number":6,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t7","workspace_id":"w1","label":"iter-alpha-007","number":7,"agent_status":"done","focused":false,"pane_count":1}
]}}
"""
            case ["herdr", "pane", "list"]:
                return """
{"result":{"panes":[
{"pane_id":"w1:p1","workspace_id":"w1","tab_id":"w1:t1","agent_status":"done"},
{"pane_id":"w1:p2","workspace_id":"w1","tab_id":"w1:t2","agent_status":"done"},
{"pane_id":"w1:p3","workspace_id":"w1","tab_id":"w1:t3","agent_status":"working"},
{"pane_id":"w1:p4","workspace_id":"w1","tab_id":"w1:t4","agent_status":"idle"},
{"pane_id":"w1:p5","workspace_id":"w1","tab_id":"w1:t5","agent_status":"done"},
{"pane_id":"w1:p6","workspace_id":"w1","tab_id":"w1:t6","agent_status":"done"},
{"pane_id":"w1:p7","workspace_id":"w1","tab_id":"w1:t7","agent_status":"done"}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[
{"agent":"codex","agent_status":"working","workspace_id":"w1","tab_id":"w1:t3","pane_id":"w1:p3","cwd":"/repo","foreground_cwd":"/repo","focused":true,"name":"iter-alpha-003"}
]}}
"""
            case ["herdr", "tab", "close", _tab_id]:
                return ""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    summaries = agents_iter_impl.close_iter_workspaces(
        workspace_name=None,
        all_workspaces=True,
        close_n_old_iters=3,
        report=lambda _message: None,
    )

    assert [command for command in commands if command[:3] == ["herdr", "tab", "close"]] == [
        ["herdr", "tab", "close", "w1:t1"],
        ["herdr", "tab", "close", "w1:t2"],
    ]
    assert [tab.tab_id for tab in summaries[0].guarded_tabs] == ["w1:t3", "w1:t4"]
    assert [tab.tab_id for tab in summaries[0].kept_tabs] == ["w1:t3", "w1:t4", "w1:t5", "w1:t6", "w1:t7"]


def test_get_iter_workspace_statuses_reports_latest_agent_iteration_status_and_closable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_herdr(args: list[str]) -> str:
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t3","agent_status":"working","focused":true,"pane_count":4,"tab_count":4}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"iter-alpha-002","number":2,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"iter-alpha-003","number":3,"agent_status":"working","focused":true,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"four","number":4,"agent_status":"idle","focused":false,"pane_count":1}
]}}
"""
            case ["herdr", "pane", "list"]:
                return """
{"result":{"panes":[
{"pane_id":"w1:p1","workspace_id":"w1","tab_id":"w1:t1","agent_status":"done"},
{"pane_id":"w1:p2","workspace_id":"w1","tab_id":"w1:t2","agent_status":"idle"},
{"pane_id":"w1:p3","workspace_id":"w1","tab_id":"w1:t3","agent_status":"working"},
{"pane_id":"w1:p4","workspace_id":"w1","tab_id":"w1:t4","agent_status":"idle"}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[
{"agent":"codex","agent_status":"idle","workspace_id":"w1","tab_id":"w1:t2","pane_id":"w1:p2","cwd":"/repo","foreground_cwd":"/repo","focused":false,"name":"iter-alpha-002"},
{"agent":"codex","agent_status":"working","workspace_id":"w1","tab_id":"w1:t3","pane_id":"w1:p3","cwd":"/repo","foreground_cwd":"/repo/src","focused":true,"name":"iter-alpha-003"}
]}}
"""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    statuses = agents_iter_impl.get_iter_workspace_statuses(close_n_old_iters=1)

    assert len(statuses) == 1
    assert statuses[0].workspace.label == "iter-alpha"
    assert statuses[0].latest_iteration == 3
    assert statuses[0].latest_agent is not None
    assert statuses[0].latest_agent.agent_status == "working"
    assert statuses[0].latest_agent.foreground_cwd == "/repo/src"
    assert statuses[0].latest_agent_tab is not None
    assert statuses[0].latest_agent_tab.label == "iter-alpha-003"
    assert [tab.label for tab in statuses[0].closable_tabs] == ["iter-alpha-001"]


def test_close_iter_workspaces_targets_one_workspace(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t5","agent_status":"done","focused":false,"pane_count":5,"tab_count":5},
{"workspace_id":"w2","label":"iter-beta","number":2,"active_tab_id":"w2:t5","agent_status":"done","focused":false,"pane_count":5,"tab_count":5}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"iter-alpha-002","number":2,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"iter-alpha-003","number":3,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"iter-alpha-004","number":4,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t5","workspace_id":"w1","label":"iter-alpha-005","number":5,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w2:t1","workspace_id":"w2","label":"iter-beta-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w2:t2","workspace_id":"w2","label":"iter-beta-002","number":2,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w2:t3","workspace_id":"w2","label":"iter-beta-003","number":3,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w2:t4","workspace_id":"w2","label":"iter-beta-004","number":4,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w2:t5","workspace_id":"w2","label":"iter-beta-005","number":5,"agent_status":"done","focused":false,"pane_count":1}
]}}
"""
            case ["herdr", "pane", "list"]:
                return """
{"result":{"panes":[
{"pane_id":"w1:p1","workspace_id":"w1","tab_id":"w1:t1","agent_status":"done"},
{"pane_id":"w1:p2","workspace_id":"w1","tab_id":"w1:t2","agent_status":"done"},
{"pane_id":"w1:p3","workspace_id":"w1","tab_id":"w1:t3","agent_status":"done"},
{"pane_id":"w1:p4","workspace_id":"w1","tab_id":"w1:t4","agent_status":"done"},
{"pane_id":"w1:p5","workspace_id":"w1","tab_id":"w1:t5","agent_status":"done"},
{"pane_id":"w2:p1","workspace_id":"w2","tab_id":"w2:t1","agent_status":"done"},
{"pane_id":"w2:p2","workspace_id":"w2","tab_id":"w2:t2","agent_status":"done"},
{"pane_id":"w2:p3","workspace_id":"w2","tab_id":"w2:t3","agent_status":"done"},
{"pane_id":"w2:p4","workspace_id":"w2","tab_id":"w2:t4","agent_status":"done"},
{"pane_id":"w2:p5","workspace_id":"w2","tab_id":"w2:t5","agent_status":"done"}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[]}}
"""
            case ["herdr", "tab", "close", _tab_id]:
                return ""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    summaries = agents_iter_impl.close_iter_workspaces(
        workspace_name="iter-alpha",
        all_workspaces=False,
        close_n_old_iters=3,
        report=lambda _message: None,
    )

    assert [summary.workspace.label for summary in summaries] == ["iter-alpha"]
    assert [command for command in commands if command[:3] == ["herdr", "tab", "close"]] == [["herdr", "tab", "close", "w1:t1"]]


def test_close_iter_workspaces_preserves_tracker_and_unknown_panes(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t7","agent_status":"done","focused":false,"pane_count":7,"tab_count":7}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-tracker","number":1,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"unknown-pane","number":2,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"iter-alpha-001","number":3,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"iter-alpha-002","number":4,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t5","workspace_id":"w1","label":"iter-alpha-003","number":5,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t6","workspace_id":"w1","label":"iter-alpha-004","number":6,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t7","workspace_id":"w1","label":"iter-alpha-005","number":7,"agent_status":"done","focused":false,"pane_count":1}
]}}
"""
            case ["herdr", "pane", "list"]:
                return """
{"result":{"panes":[
{"pane_id":"w1:p1","workspace_id":"w1","tab_id":"w1:t1","agent_status":"idle"},
{"pane_id":"w1:p2","workspace_id":"w1","tab_id":"w1:t2","agent_status":"unknown"},
{"pane_id":"w1:p3","workspace_id":"w1","tab_id":"w1:t3","agent_status":"done"},
{"pane_id":"w1:p4","workspace_id":"w1","tab_id":"w1:t4","agent_status":"done"},
{"pane_id":"w1:p5","workspace_id":"w1","tab_id":"w1:t5","agent_status":"done"},
{"pane_id":"w1:p6","workspace_id":"w1","tab_id":"w1:t6","agent_status":"done"},
{"pane_id":"w1:p7","workspace_id":"w1","tab_id":"w1:t7","agent_status":"done"}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[]}}
"""
            case ["herdr", "tab", "close", _tab_id]:
                return ""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    summaries = agents_iter_impl.close_iter_workspaces(
        workspace_name="iter-alpha",
        all_workspaces=False,
        close_n_old_iters=3,
        report=lambda _message: None,
    )

    assert [tab.tab_id for tab in summaries[0].guarded_tabs] == ["w1:t1", "w1:t2"]
    assert [command for command in commands if command[:3] == ["herdr", "tab", "close"]] == [["herdr", "tab", "close", "w1:t3"]]


def test_check_iter_workspace_budget_closes_workspace_after_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    reports: list[str] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t2","agent_status":"working","focused":false,"pane_count":2,"tab_count":2}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-100","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"iter-alpha-101","number":2,"agent_status":"working","focused":true,"pane_count":1}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[]}}
"""
            case ["herdr", "workspace", "close", "w1"]:
                return ""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    result = agents_iter_impl.check_iter_workspace_budget(workspace_name="iter-alpha", max_iterations=100, report=reports.append)

    assert result.closed is True
    assert result.latest_iteration == 101
    assert ["herdr", "workspace", "close", "w1"] in commands
    assert "iter-alpha: latest=101 exceeded budget=100; closing workspace." in reports


def test_check_iter_workspace_budget_keeps_workspace_at_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    reports: list[str] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t1","agent_status":"working","focused":false,"pane_count":1,"tab_count":1}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-100","number":1,"agent_status":"working","focused":true,"pane_count":1}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[
{"agent":"codex","agent_status":"working","workspace_id":"w1","tab_id":"w1:t1","pane_id":"w1:p1","cwd":"/repo","foreground_cwd":"/repo","focused":true,"name":"iter-alpha-100"}
]}}
"""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    result = agents_iter_impl.check_iter_workspace_budget(workspace_name="iter-alpha", max_iterations=100, report=reports.append)

    assert result.closed is False
    assert result.latest_iteration == 100
    assert ["herdr", "workspace", "close", "w1"] not in commands
    assert "iter-alpha: latest=100, budget=100; keeping workspace open." in reports


def test_track_iter_workspace_once_reports_status_and_closes_old_iters(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    reports: list[str] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t5","agent_status":"idle","focused":false,"pane_count":5,"tab_count":5}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"iter-alpha-001","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"iter-alpha-002","number":2,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"iter-alpha-003","number":3,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"iter-alpha-004","number":4,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t5","workspace_id":"w1","label":"iter-alpha-005","number":5,"agent_status":"idle","focused":true,"pane_count":1}
]}}
"""
            case ["herdr", "pane", "list"]:
                return """
{"result":{"panes":[
{"pane_id":"w1:p1","workspace_id":"w1","tab_id":"w1:t1","agent_status":"done"},
{"pane_id":"w1:p2","workspace_id":"w1","tab_id":"w1:t2","agent_status":"idle"},
{"pane_id":"w1:p3","workspace_id":"w1","tab_id":"w1:t3","agent_status":"idle"},
{"pane_id":"w1:p4","workspace_id":"w1","tab_id":"w1:t4","agent_status":"idle"},
{"pane_id":"w1:p5","workspace_id":"w1","tab_id":"w1:t5","agent_status":"idle"}
]}}
"""
            case ["herdr", "agent", "list"]:
                return """
{"result":{"agents":[
{"agent":"codex","agent_status":"idle","workspace_id":"w1","tab_id":"w1:t5","pane_id":"w1:p5","cwd":"/repo","foreground_cwd":"/repo","focused":true,"name":"iter-alpha-005"}
]}}
"""
            case ["herdr", "tab", "close", "w1:t1"]:
                return ""
            case _:
                raise AssertionError(args)

    monkeypatch.setattr(agents_iter_impl, "_run_herdr", fake_run_herdr)

    check = agents_iter_impl.track_iter_workspace_once(
        workspace_name="iter-alpha",
        max_iterations=10,
        close_n_old_iters=3,
        report=reports.append,
    )

    assert check.status.latest_iteration == 5
    assert check.budget.closed is False
    assert check.close_summary is not None
    assert [tab.tab_id for tab in check.close_summary.closed_tabs] == ["w1:t1"]
    assert ["herdr", "workspace", "close", "w1"] not in commands
    assert ["herdr", "tab", "close", "w1:t1"] in commands
    assert "iter-alpha: iter=005 agent=codex status=idle tabs=5 close=1 guard=0." in reports
    assert "iter-alpha: latest=005, budget=010; keeping workspace open." in reports
