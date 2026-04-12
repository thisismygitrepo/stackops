from __future__ import annotations

import json
from pathlib import Path
import platform as platform_module
import sys
from types import ModuleType

import pytest

from machineconfig.scripts.python.helpers.helpers_sessions import utils as subject


def install_module(monkeypatch: pytest.MonkeyPatch, name: str, module: ModuleType) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def test_balance_load_writes_adjusted_layout_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    layout_path = tmp_path / "layout.json"
    layout_path.write_text(
        json.dumps({"layouts": [{"layoutName": "alpha", "layoutTabs": [{"tabName": "one", "startDir": ".", "command": "echo"}]}]}), encoding="utf-8"
    )
    calls: list[str] = []
    load_balancer_module = ModuleType("machineconfig.cluster.sessions_managers.utils.load_balancer")

    def limit_tab_num(layout_configs: list[dict[str, object]], max_thresh: int, threshold_type: str, breaking_method: str) -> list[dict[str, object]]:
        calls.append(f"{len(layout_configs)}:{max_thresh}:{threshold_type}:{breaking_method}")
        return [{"layoutName": "adjusted", "layoutTabs": []}]

    load_balancer_module.limit_tab_num = limit_tab_num
    install_module(monkeypatch, "machineconfig.cluster.sessions_managers.utils.load_balancer", load_balancer_module)

    subject.balance_load(layout_path=str(layout_path), max_thresh=5, thresh_type="w", breaking_method="ct", output_path=None)

    output_path = tmp_path / "layout_adjusted_5_w_ct.json"
    assert calls == ["1:5:weight:combineTabs"]
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"layouts": [{"layoutName": "adjusted", "layoutTabs": []}]}


def test_create_template_writes_layout_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home_dir = tmp_path / "home"
    project_dir = home_dir / "project"
    project_dir.mkdir(parents=True)
    monkeypatch.setattr(subject.Path, "home", lambda: home_dir)
    monkeypatch.chdir(project_dir)
    monkeypatch.setattr(platform_module, "system", lambda: "Linux")

    subject.create_template(name="custom.json", num_tabs=2)

    layout_path = project_dir / "custom.json"
    first_payload = json.loads(layout_path.read_text(encoding="utf-8"))
    assert first_payload["layouts"][0]["layoutName"] == "projectLayout"
    assert first_payload["layouts"][0]["layoutTabs"] == [
        {"tabName": "Tab1", "startDir": "~/project", "command": "bash"},
        {"tabName": "Tab2", "startDir": "~/project", "command": "bash"},
    ]

    original_text = layout_path.read_text(encoding="utf-8")
    subject.create_template(name="custom.json", num_tabs=2)

    assert layout_path.read_text(encoding="utf-8") == original_text
    assert "already exists" in capsys.readouterr().out
