

from pathlib import Path
import sys
from types import ModuleType

import pytest
import typer

from stackops.scripts.python.helpers.helpers_sessions import sessions_multiprocess as subject
from stackops.utils.schemas.layouts.layout_types import LayoutConfig, TabConfig


def install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def test_create_from_function_builds_layout_from_directory_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script_path = tmp_path / "worker.py"
    script_path.write_text("print('hi')\n", encoding="utf-8")
    call_log: list[str] = []
    captured_layouts: list[LayoutConfig] = []

    path_helper_module = ModuleType("stackops.utils.path_helper")
    options_module = ModuleType("stackops.utils.options")
    accessories_module = ModuleType("stackops.utils.accessories")
    ve_module = ModuleType("stackops.utils.ve")
    fire_helper_module = ModuleType(
        "stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper"
    )
    zellij_module = ModuleType("stackops.cluster.sessions_managers.zellij.zellij_local")

    def sanitize_path(path: str) -> Path:
        assert path == str(tmp_path)
        return tmp_path

    def match_file_name(sub_string: str, search_root: Path, suffixes: set[str]) -> Path:
        raise AssertionError(f"unexpected match_file_name call: {sub_string} {search_root} {suffixes}")

    def search_for_files_of_interest(path_obj: Path, suffixes: set[str]) -> list[str]:
        call_log.append(f"search:{path_obj}:{sorted(suffixes)}")
        return [str(script_path)]

    def choose_from_options(
        multi: bool,
        options: list[str],
        tv: bool,
        msg: str,
    ) -> str | None:
        call_log.append(f"choose:{multi}:{tv}:{msg}")
        assert options == [str(script_path)]
        return str(script_path)

    def get_repo_root(choice_file: Path) -> Path:
        call_log.append(f"repo:{choice_file}")
        return tmp_path

    def get_ve_path_and_ipython_profile(choice_file: Path) -> tuple[Path | None, str | None]:
        call_log.append(f"ve:{choice_file}")
        return (tmp_path / ".venv" / "bin" / "python", None)

    def choose_function_or_lines(
        choice_file: Path,
        kwargs_dict: dict[str, object],
    ) -> tuple[str, Path, dict[str, object]]:
        call_log.append(f"function:{choice_file}:{kwargs_dict}")
        return ("main", choice_file, kwargs_dict)

    def run_zellij_layout(
        layout_config: LayoutConfig,
        on_conflict: str,
    ) -> None:
        captured_layouts.append(layout_config)
        call_log.append(f"run:{on_conflict}")

    setattr(path_helper_module, "sanitize_path", sanitize_path)
    setattr(path_helper_module, "match_file_name", match_file_name)
    setattr(path_helper_module, "search_for_files_of_interest", search_for_files_of_interest)
    setattr(options_module, "choose_from_options", choose_from_options)
    setattr(accessories_module, "get_repo_root", get_repo_root)
    setattr(ve_module, "get_ve_path_and_ipython_profile", get_ve_path_and_ipython_profile)
    setattr(fire_helper_module, "choose_function_or_lines", choose_function_or_lines)
    setattr(zellij_module, "run_zellij_layout", run_zellij_layout)
    install_module(monkeypatch, "stackops.utils.path_helper", path_helper_module)
    install_module(monkeypatch, "stackops.utils.options", options_module)
    install_module(monkeypatch, "stackops.utils.accessories", accessories_module)
    install_module(monkeypatch, "stackops.utils.ve", ve_module)
    install_module(
        monkeypatch,
        "stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper",
        fire_helper_module,
    )
    install_module(
        monkeypatch,
        "stackops.cluster.sessions_managers.zellij.zellij_local",
        zellij_module,
    )

    subject.create_from_function(
        num_process=2,
        path=str(tmp_path),
        function=None,
    )

    assert call_log == [
        f"search:{tmp_path}:{['.ps1', '.py', '.sh']}",
        "choose:False:True:Choose one option",
        f"repo:{script_path}",
        f"ve:{script_path}",
        f"function:{script_path}:{{}}",
        "run:error",
    ]
    assert len(captured_layouts) == 1
    tabs: list[TabConfig] = captured_layouts[0]["layoutTabs"]
    assert len(tabs) == 2
    expected_start_dir = str((tmp_path / ".venv" / "bin").resolve())
    for index, tab in enumerate(tabs):
        assert tab["tabName"] == f"tab{index}"
        assert tab["startDir"] == expected_start_dir
        assert tab["command"] == (
            f"uv run python -m fire {script_path} main --idx={index} --idx_max=2"
        )
    assert f"Selected file: {script_path}." in capsys.readouterr().out


def test_create_from_function_exits_when_directory_selection_is_cancelled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path_helper_module = ModuleType("stackops.utils.path_helper")
    options_module = ModuleType("stackops.utils.options")

    def sanitize_path(path: str) -> Path:
        return tmp_path

    def match_file_name(sub_string: str, search_root: Path, suffixes: set[str]) -> Path:
        raise AssertionError(f"unexpected match_file_name call: {sub_string} {search_root} {suffixes}")

    def search_for_files_of_interest(path_obj: Path, suffixes: set[str]) -> list[str]:
        return [str(tmp_path / "worker.py")]

    def choose_from_options(
        multi: bool,
        options: list[str],
        tv: bool,
        msg: str,
    ) -> str | None:
        return None

    setattr(path_helper_module, "sanitize_path", sanitize_path)
    setattr(path_helper_module, "match_file_name", match_file_name)
    setattr(path_helper_module, "search_for_files_of_interest", search_for_files_of_interest)
    setattr(options_module, "choose_from_options", choose_from_options)
    install_module(monkeypatch, "stackops.utils.path_helper", path_helper_module)
    install_module(monkeypatch, "stackops.utils.options", options_module)

    with pytest.raises(typer.Exit) as exc_info:
        subject.create_from_function(
            num_process=1,
            path=str(tmp_path),
            function="main",
        )

    assert exc_info.value.exit_code == 1
