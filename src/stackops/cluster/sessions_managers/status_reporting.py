from typing import Any


def calculate_global_summary_from_status(
    all_status: dict[str, dict[str, Any]],
    include_remote_machines: bool = False,
) -> dict[str, Any]:
    total_sessions = len(all_status)
    healthy_sessions = sum(
        1
        for status in all_status.values()
        if status.get("summary", {}).get("session_healthy", False)
    )
    total_commands = sum(
        status.get("summary", {}).get("total_commands", 0)
        for status in all_status.values()
    )
    total_running = sum(
        status.get("summary", {}).get("running_commands", 0)
        for status in all_status.values()
    )

    result: dict[str, Any] = {
        "total_sessions": total_sessions,
        "healthy_sessions": healthy_sessions,
        "unhealthy_sessions": total_sessions - healthy_sessions,
        "total_commands": total_commands,
        "running_commands": total_running,
        "stopped_commands": total_commands - total_running,
        "all_sessions_healthy": healthy_sessions == total_sessions,
        "all_commands_running": total_running == total_commands,
    }

    if include_remote_machines:
        result["remote_machines"] = list(
            {
                status.get("remote_name", "")
                for status in all_status.values()
                if "remote_name" in status
            }
        )

    return result
