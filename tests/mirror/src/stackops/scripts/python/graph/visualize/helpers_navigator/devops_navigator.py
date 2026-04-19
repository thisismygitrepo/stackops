

import sys
from types import ModuleType

from pytest import MonkeyPatch

from stackops.scripts.python.graph.visualize.helpers_navigator import devops_navigator


def test_main_imports_main_app_lazily_and_runs_it(monkeypatch: MonkeyPatch) -> None:
    module_name = "stackops.scripts.python.graph.visualize.helpers_navigator.main_app"
    calls: list[str] = []

    class FakeApp:
        def run(self) -> None:
            calls.append("run")

    fake_module = ModuleType(module_name)
    setattr(fake_module, "CommandNavigatorApp", FakeApp)
    monkeypatch.setitem(sys.modules, module_name, fake_module)

    devops_navigator.main()

    assert calls == ["run"]
