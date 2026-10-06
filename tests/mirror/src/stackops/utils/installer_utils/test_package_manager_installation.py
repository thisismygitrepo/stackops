import subprocess
from unittest.mock import Mock

import pytest

from stackops.utils.installer_utils import package_manager_installation


@pytest.mark.parametrize("returncode", (2316632107, -1978335189))
@pytest.mark.parametrize("operation", ("install", "upgrade"))
def test_winget_no_applicable_update_is_a_distinct_no_change_result(returncode: int, operation: str, monkeypatch: pytest.MonkeyPatch) -> None:
    command = f"""winget {operation} --id Microsoft.PowerShell --source winget"""
    run = Mock(return_value=subprocess.CompletedProcess[str](args=command, returncode=returncode))
    monkeypatch.setattr(package_manager_installation.subprocess, "run", run)

    result = package_manager_installation.install_with_package_manager(command=command, requested_version=None)

    assert result == "no_applicable_update"
    run.assert_called_once_with(command, shell=True, capture_output=False, text=True, encoding="utf-8", check=False)


@pytest.mark.parametrize(
    ("command", "requested_version", "returncode"),
    (
        ("winget install --id Microsoft.PowerShell", "7.7.0", 2316632107),
        ("winget install --id Microsoft.PowerShell", "7.7.0", -1978335189),
        ("winget install --id Microsoft.PowerShell --version 7.7.0", None, 2316632107),
        ("winget install --id Microsoft.PowerShell --version=7.7.0", None, 2316632107),
        ("winget install --id Microsoft.PowerShell -v 7.7.0", None, 2316632107),
        ("winget uninstall --id Microsoft.PowerShell", None, 2316632107),
        ("npm install example", None, 2316632107),
        ("npm install example", None, -1978335189),
        ("winget install --id Microsoft.PowerShell", None, 1),
    ),
)
def test_no_update_code_does_not_hide_unsatisfied_version_requests_or_other_failures(
    command: str, requested_version: str | None, returncode: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = Mock(return_value=subprocess.CompletedProcess[str](args=command, returncode=returncode))
    monkeypatch.setattr(package_manager_installation.subprocess, "run", run)

    with pytest.raises(RuntimeError, match=f"""failed with return code {returncode}"""):
        package_manager_installation.install_with_package_manager(command=command, requested_version=requested_version)


def test_zero_returncode_remains_successful(monkeypatch: pytest.MonkeyPatch) -> None:
    command = "winget install --id Microsoft.PowerShell --version 7.7.0"
    run = Mock(return_value=subprocess.CompletedProcess[str](args=command, returncode=0))
    monkeypatch.setattr(package_manager_installation.subprocess, "run", run)

    result = package_manager_installation.install_with_package_manager(command=command, requested_version="7.7.0")

    assert result == "installed"
