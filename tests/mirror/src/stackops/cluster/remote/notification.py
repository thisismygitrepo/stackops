from __future__ import annotations

from stackops.cluster.remote.models import EmailParams
from stackops.cluster.remote.notification import render_notification_block


def test_render_notification_block_keeps_runtime_placeholders() -> None:
    block = render_notification_block(
        EmailParams(
            addressee="alice",
            speaker="worker-1",
            ssh_conn_str="user@example",
            executed_obj="repo/task.py",
            email_config_name="alerts",
            to_email="ops@example.com",
            file_manager_path="/tmp/file_manager.json",
        )
    )

    assert "alice" in block
    assert "worker-1" in block
    assert "repo/task.py" in block
    assert "user@example" in block
    assert "ops@example.com" in block
    assert "Error: `{params.error_message}`" in block
    assert 'subject=f"Job completed: {manager.job_id}"' in block
