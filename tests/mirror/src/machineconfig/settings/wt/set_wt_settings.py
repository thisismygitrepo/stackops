from __future__ import annotations

import importlib
import platform
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from types import ModuleType
from typing import Protocol, cast

import pytest


MODULE_NAME = "machineconfig.settings.wt.set_wt_settings"


class TerminalSettingsObject(Protocol):
    path: "FakePath"
    dat: dict[str, object]
    profs: list[dict[str, object]]

    def update_default_settings(self) -> None: ...

    def customize_powershell(self, nerd_font: bool = True) -> None: ...

    def make_powershell_default_profile(self) -> None: ...

    def save_terminal_settings(self) -> None: ...


@dataclass(slots=True)
class FakePath:
    value: str

    def joinpath(self, suffix: str) -> "FakePath":
        return FakePath(value=f"{self.value}/{suffix}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class SaveJsonCall:
    obj: dict[str, object]
    path: FakePath
    indent: int


def _remove_module() -> None:
    sys.modules.pop(MODULE_NAME, None)


def _import_for_platform(monkeypatch: pytest.MonkeyPatch, platform_name: str) -> ModuleType:
    _remove_module()
    monkeypatch.setattr(platform, "system", lambda: platform_name)
    return importlib.import_module(MODULE_NAME)


def test_import_rejects_non_windows_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(AssertionError, match="only for Windows"):
        _import_for_platform(monkeypatch=monkeypatch, platform_name="Linux")
    _remove_module()


def test_terminal_settings_updates_profiles_and_saves(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _import_for_platform(monkeypatch=monkeypatch, platform_name="Windows")
    console = getattr(module, "console")
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)
    monkeypatch.setenv("LOCALAPPDATA", "/tmp/local-app-data")
    monkeypatch.setattr(module, "PathExtended", FakePath)
    monkeypatch.setattr(module, "randstr", lambda: "backup")
    backup_calls: list[tuple[FakePath, str]] = []

    initial_data: dict[str, object] = {
        "profiles": {"list": [{"name": "PowerShell", "guid": "{pwsh-guid}"}, {"name": "Command Prompt", "guid": "{cmd-guid}"}], "defaults": {}},
        "actions": [],
    }
    save_calls: list[SaveJsonCall] = []

    def fake_read_json(path: FakePath) -> dict[str, object]:
        assert path.value.endswith("settings.json")
        return initial_data

    def fake_save_json(*, obj: dict[str, object], path: FakePath, indent: int) -> None:
        save_calls.append(SaveJsonCall(obj=obj, path=path, indent=indent))

    monkeypatch.setattr(module.path_core, "copy", lambda path, *, append: backup_calls.append((path, append)))
    monkeypatch.setattr(module, "read_json", fake_read_json)
    monkeypatch.setattr(module, "save_json", fake_save_json)

    terminal_settings_type = cast(type[TerminalSettingsObject], getattr(module, "TerminalSettings"))
    terminal_settings = terminal_settings_type()
    terminal_settings.update_default_settings()
    terminal_settings.customize_powershell(nerd_font=True)
    terminal_settings.make_powershell_default_profile()
    terminal_settings.save_terminal_settings()

    assert backup_calls == [(terminal_settings.path, ".orig_backup")]
    assert terminal_settings.dat["startOnUserLogin"] is True
    assert terminal_settings.dat["launchMode"] == "fullscreen"
    assert terminal_settings.dat["theme"] == "dark"
    assert terminal_settings.dat["focusFollowMouse"] is True
    assert terminal_settings.dat["copyOnSelect"] is True
    profiles_section = cast(dict[str, object], terminal_settings.dat["profiles"])
    defaults = cast(dict[str, object], profiles_section["defaults"])
    assert defaults["padding"] == "0"
    assert defaults["useAcrylic"] is False
    powershell_profile = terminal_settings.profs[0]
    assert powershell_profile["commandline"] == "pwsh"
    assert powershell_profile["opacity"] == 87
    assert powershell_profile["startingDirectory"] == "%USERPROFILE%"
    assert powershell_profile["font"] == {"face": "CaskaydiaCove Nerd Font"}
    assert terminal_settings.dat["defaultProfile"] == "{pwsh-guid}"
    assert save_calls == [SaveJsonCall(obj=terminal_settings.dat, path=terminal_settings.path, indent=5)]
    _remove_module()


def test_main_runs_terminal_setup_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _import_for_platform(monkeypatch=monkeypatch, platform_name="Windows")
    console = getattr(module, "console")
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: None)
    monkeypatch.setattr(module, "render_banner", lambda *args, **kwargs: None)

    call_log: list[str] = []
    created_instances: list[FakeMainTerminalSettings] = []

    class FakeMainTerminalSettings:
        def __init__(self) -> None:
            self.dat: dict[str, object] = {"actions": []}
            created_instances.append(self)
            call_log.append("init")

        def update_default_settings(self) -> None:
            call_log.append("defaults")

        def customize_powershell(self, nerd_font: bool = True) -> None:
            assert nerd_font is True
            call_log.append("powershell")

        def make_powershell_default_profile(self) -> None:
            call_log.append("default-profile")

        def save_terminal_settings(self) -> None:
            call_log.append("save")

    monkeypatch.setattr(module, "TerminalSettings", FakeMainTerminalSettings)

    main = cast(Callable[[], None], getattr(module, "main"))
    main()

    assert call_log == ["init", "defaults", "powershell", "default-profile", "save"]
    assert len(created_instances) == 1
    actions = cast(list[dict[str, str]], created_instances[0].dat["actions"])
    assert actions == [{"command": "togglePaneZoom", "keys": "ctrl+shift+z"}]
    _remove_module()
