from stackops.scripts.python.helpers.helpers_sessions import sessions_dynamic_display


def test_active_tasks_table_hides_directory_and_command_columns() -> None:
    active_tasks: tuple[sessions_dynamic_display.DynamicTabTask, ...] = (
        {
            "index": 0,
            "runtime_tab_name": "tab__dynamic_1",
            "tab": {
                "tabName": "tab",
                "startDir": "/workspace/project",
                "command": "uv run app.py",
            },
        },
    )

    table = sessions_dynamic_display._build_active_tasks_table(active_tasks=active_tasks)

    assert [column.header for column in table.columns] == ["#", "Status", "Runtime Tab"]


def test_recent_completed_table_shows_duration_column() -> None:
    completed_tasks: tuple[sessions_dynamic_display.DynamicTabTask, ...] = (
        {
            "index": 0,
            "runtime_tab_name": "tab__dynamic_1",
            "tab": {
                "tabName": "tab",
                "startDir": "/workspace/project",
                "command": "uv run app.py",
            },
            "completion_duration_seconds": 2.0,
        },
    )

    table = sessions_dynamic_display._build_recent_completed_table(recent_completed_tasks=completed_tasks)

    assert [column.header for column in table.columns] == ["#", "Runtime Tab", "Duration"]
    assert table.columns[2]._cells == ["00:02"]
