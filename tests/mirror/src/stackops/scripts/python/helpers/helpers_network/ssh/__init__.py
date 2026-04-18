import sys
import types

import pytest

import stackops.scripts.python.helpers.helpers_network.ssh as subject


@pytest.mark.parametrize(
    ("os_name", "module_name", "function_name", "expected"),
    [
        (
            "Linux",
            "stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_linux",
            "ssh_debug_linux",
            {"linux": {"ok": True}},
        ),
        (
            "Darwin",
            "stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_darwin",
            "ssh_debug_darwin",
            {"darwin": {"ok": True}},
        ),
        (
            "Windows",
            "stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_windows",
            "ssh_debug_windows",
            {"windows": {"ok": True}},
        ),
    ],
)
def test_ssh_debug_dispatches_by_platform(
    monkeypatch: pytest.MonkeyPatch,
    os_name: str,
    module_name: str,
    function_name: str,
    expected: dict[str, dict[str, bool]],
) -> None:
    debug_module = types.ModuleType(module_name)
    setattr(debug_module, function_name, lambda: expected)
    monkeypatch.setitem(sys.modules, module_name, debug_module)
    monkeypatch.setattr(subject, "system", lambda: os_name)

    result = subject.ssh_debug()

    assert result == expected



def test_ssh_debug_raises_for_unsupported_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(subject, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="ssh_debug is not supported on Plan9"):
        subject.ssh_debug()



def test_module_exports_only_ssh_debug() -> None:
    assert subject.__all__ == ["ssh_debug"]
