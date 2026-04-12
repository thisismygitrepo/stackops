from __future__ import annotations

from machineconfig.cluster.remote.execution_script import render_execution_script


def test_render_execution_script_inserts_runtime_inputs() -> None:
    script = render_execution_script(
        params_json_path="/tmp/job_params.json",
        file_manager_json_path="/tmp/file_manager.json",
        execution_line="res = func(**func_kwargs)",
        notification_block="print('notify')",
    )

    assert 'JobParams.from_dict(read_json(Path(r"/tmp/job_params.json").expanduser()))' in script
    assert 'FileManager.from_json_file(r"/tmp/file_manager.json")' in script
    assert "manager.secure_resources()" in script
    assert "res = func(**func_kwargs)" in script
    assert "print('notify')" in script
    assert "JOB COMPLETED | id={manager.job_id}" in script
    assert "manager.unlock_resources()" in script
