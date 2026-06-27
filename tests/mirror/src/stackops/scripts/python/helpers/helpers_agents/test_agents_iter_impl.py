import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_iter_impl


def test_clean_iter_workspaces_closes_all_but_last_three_tabs(monkeypatch: pytest.MonkeyPatch) -> None:
    commands: list[list[str]] = []
    reports: list[str] = []

    def fake_run_herdr(args: list[str]) -> str:
        commands.append(args)
        match args:
            case ["herdr", "workspace", "list"]:
                return """
{"result":{"workspaces":[
{"workspace_id":"w1","label":"iter-alpha","number":1,"active_tab_id":"w1:t4","agent_status":"working","focused":false,"pane_count":4,"tab_count":4},
{"workspace_id":"w2","label":"main","number":2,"active_tab_id":"w2:t1","agent_status":"idle","focused":false,"pane_count":1,"tab_count":1},
{"workspace_id":"w3","label":"iter-beta","number":3,"active_tab_id":"w3:t2","agent_status":"done","focused":false,"pane_count":2,"tab_count":2}
]}}
"""
            case ["herdr", "tab", "list"]:
                return """
{"result":{"tabs":[
{"tab_id":"w1:t1","workspace_id":"w1","label":"one","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"two","number":2,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"three","number":3,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"four","number":4,"agent_status":"working","focused":true,"pane_count":1},
{"tab_id":"w2:t1","workspace_id":"w2","label":"main","number":1,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w3:t1","workspace_id":"w3","label":"one","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w3:t2","workspace_id":"w3","label":"two","number":2,"agent_status":"done","focused":false,"pane_count":1}
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

    summaries = agents_iter_impl.clean_iter_workspaces(report=reports.append)

    assert [command for command in commands if command[:3] == ["herdr", "tab", "close"]] == [["herdr", "tab", "close", "w1:t1"]]
    assert [summary.workspace.label for summary in summaries] == ["iter-alpha", "iter-beta"]
    assert len(summaries[0].kept_tabs) == 3
    assert len(summaries[1].closed_tabs) == 0
    assert "Planning iter cleanup: 2 workspace(s), 6 tab(s), closing 1" in reports[0]
    assert "Closing 1/1: iter-alpha tab #1 one [done] w1:t1" in reports


def test_clean_iter_workspaces_keeps_next_tab_after_running_agent(monkeypatch: pytest.MonkeyPatch) -> None:
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
{"tab_id":"w1:t1","workspace_id":"w1","label":"one","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"two","number":2,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"three","number":3,"agent_status":"working","focused":true,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"four","number":4,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t5","workspace_id":"w1","label":"five","number":5,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t6","workspace_id":"w1","label":"six","number":6,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t7","workspace_id":"w1","label":"seven","number":7,"agent_status":"done","focused":false,"pane_count":1}
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

    summaries = agents_iter_impl.clean_iter_workspaces(report=lambda _message: None)

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
{"tab_id":"w1:t1","workspace_id":"w1","label":"one","number":1,"agent_status":"done","focused":false,"pane_count":1},
{"tab_id":"w1:t2","workspace_id":"w1","label":"two","number":2,"agent_status":"idle","focused":false,"pane_count":1},
{"tab_id":"w1:t3","workspace_id":"w1","label":"three","number":3,"agent_status":"working","focused":true,"pane_count":1},
{"tab_id":"w1:t4","workspace_id":"w1","label":"four","number":4,"agent_status":"idle","focused":false,"pane_count":1}
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

    statuses = agents_iter_impl.get_iter_workspace_statuses()

    assert len(statuses) == 1
    assert statuses[0].workspace.label == "iter-alpha"
    assert statuses[0].latest_iteration == 3
    assert statuses[0].latest_agent is not None
    assert statuses[0].latest_agent.agent_status == "working"
    assert statuses[0].latest_agent.foreground_cwd == "/repo/src"
    assert statuses[0].latest_agent_tab is not None
    assert statuses[0].latest_agent_tab.label == "three"
    assert [tab.label for tab in statuses[0].closable_tabs] == ["one"]
