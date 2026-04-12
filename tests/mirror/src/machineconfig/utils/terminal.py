from __future__ import annotations

import io
import subprocess
from pathlib import Path

from machineconfig.utils.path_extended import PathExtended
from machineconfig.utils.terminal import Response


def test_response_from_completed_process_preserves_io_and_strips_on_call() -> None:
    completed_process = subprocess.CompletedProcess(
        args="echo hi",
        returncode=0,
        stdout="value\n",
        stderr="",
    )

    response = Response.from_completed_process(completed_process)

    assert response.op == "value\n"
    assert response.returncode == 0
    assert response() == "value"


def test_response_capture_and_path_helpers_work_together(tmp_path: Path) -> None:
    stdin = io.BytesIO(b"input\n")
    stdout = io.BytesIO(f"{tmp_path}/artifact\n".encode())
    stderr = io.BytesIO(b"")

    response = Response(
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        cmd="cmd",
        desc="desc",
    ).capture()

    path_value = response.op2path(strict_returncode=True, strict_err=True)
    assert isinstance(path_value, PathExtended)
    assert str(path_value) == str(tmp_path / "artifact")
    assert response.op_if_successfull_or_default(
        strict_returcode=True,
        strict_err=True,
    ) == f"{tmp_path}/artifact\n"


def test_response_success_state_respects_strict_stderr() -> None:
    response = Response(cmd="cmd")
    response.output.stderr = "boom"

    assert response.is_successful(strict_returcode=True, strict_err=False)
    assert not response.is_successful(strict_returcode=True, strict_err=True)
