import subprocess
import sys
from types import ModuleType

import pytest

from stackops.scripts.python.helpers.helpers_utils import specs


def test_get_cpu_name_uses_powershell_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(specs.platform, "system", lambda: "Windows")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
        command = args[0]
        assert command == ["pwsh", "-NoProfile", "-Command", "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name | Select-Object -First 1"]
        return subprocess.CompletedProcess(args=command, returncode=0, stdout="AMD Ryzen 7 8845HS\n", stderr="")

    monkeypatch.setattr(specs.subprocess, "run", fake_run)

    assert specs.get_cpu_name() == "AMD Ryzen 7 8845HS"


def test_get_cpu_name_falls_back_to_registry_when_powershell_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(specs.platform, "system", lambda: "Windows")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise FileNotFoundError("powershell is unavailable")

    class _FakeRegistryKey:
        def __enter__(self) -> object:
            return object()

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            del exc_type, exc, tb

    fake_winreg = ModuleType("winreg")
    fake_winreg.HKEY_LOCAL_MACHINE = object()  # type: ignore[attr-defined]
    fake_winreg.OpenKey = lambda root, path: _FakeRegistryKey()  # type: ignore[attr-defined]
    fake_winreg.QueryValueEx = lambda key, name: ("Intel(R) Core(TM) Ultra 9 185H", 1)  # type: ignore[attr-defined]

    monkeypatch.setattr(specs.subprocess, "run", fake_run)
    monkeypatch.setitem(sys.modules, "winreg", fake_winreg)

    assert specs.get_cpu_name() == "Intel(R) Core(TM) Ultra 9 185H"
