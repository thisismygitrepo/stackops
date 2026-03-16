import subprocess
from unittest.mock import patch

from machineconfig.utils import code


def test_run_shell_file_returns_cancelled_process_without_raising() -> None:
    cancelled_process: subprocess.CompletedProcess[bytes] = subprocess.CompletedProcess(args="bash /tmp/test.sh", returncode=130)

    with (
        patch("platform.system", return_value="Linux"),
        patch.object(code.subprocess, "run", return_value=cancelled_process) as subprocess_run,
    ):
        result = code.run_shell_file(script_path="/tmp/test.sh", clean_env=False)

    assert result.returncode == 130
    subprocess_run.assert_called_once_with("bash /tmp/test.sh", check=False, shell=True, env=None)
