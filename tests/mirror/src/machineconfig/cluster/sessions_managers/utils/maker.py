from collections.abc import Callable
import inspect
from pathlib import Path
import platform
import sys
from types import ModuleType

from machineconfig.cluster.sessions_managers.utils import maker
from machineconfig.utils.schemas.layouts.layout_types import TabConfig


def test_get_fire_tab_using_uv_wraps_named_function() -> None:
    call_names: list[str] = []
    executed: list[str] = []

    def sample_fn() -> None:
        executed.append("sample_fn")

    def fake_lambda_to_python_script(
        func: Callable[[], object],
        in_global: bool,
        import_module: bool,
    ) -> str:
        assert in_global is True
        assert import_module is False
        call_names.append(func.__name__)
        func()
        return "print('ok')"

    def fake_uv_command(
        python_script: str,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        uv_run_flags: str,
    ) -> tuple[str, Path]:
        assert python_script == "print('ok')"
        assert uv_with == ["rich"]
        assert uv_project_dir == "/work/app"
        assert uv_run_flags == "--quiet"
        return ("uv run generated.py", Path("/tmp/generated.py"))

    fake_meta = ModuleType("machineconfig.utils.meta")
    setattr(fake_meta, "lambda_to_python_script", fake_lambda_to_python_script)
    fake_code = ModuleType("machineconfig.utils.code")
    setattr(fake_code, "get_uv_command_executing_python_script", fake_uv_command)
    sys.modules["machineconfig.utils.meta"] = fake_meta
    sys.modules["machineconfig.utils.code"] = fake_code

    tab_config, artifact_path = maker.get_fire_tab_using_uv(
        func=sample_fn,
        tab_weight=3,
        import_module=False,
        uv_with=["rich"],
        uv_project_dir="/work/app",
        start_dir="/work/app",
        uv_run_flags="--quiet",
    )

    assert call_names == ["<lambda>"]
    assert executed == ["sample_fn"]
    assert tab_config == {
        "command": "uv run generated.py",
        "startDir": "/work/app",
        "tabName": "sample_fn",
        "tabWeight": 3,
    }
    assert artifact_path == Path("/tmp/generated.py")


def test_get_fire_tab_using_fire_builds_linux_command() -> None:
    fake_source_of_truth = ModuleType("machineconfig.utils.source_of_truth")
    setattr(fake_source_of_truth, "CONFIG_ROOT", Path("/config"))
    sys.modules["machineconfig.utils.source_of_truth"] = fake_source_of_truth

    def fake_system() -> str:
        return "Linux"

    def fake_getfile(_func: Callable[[], object]) -> str:
        return "/tmp/home/work/tool.py"

    def fake_home() -> Path:
        return Path("/tmp/home")

    platform.system = fake_system
    inspect.getfile = fake_getfile
    maker.Path.home = fake_home

    def sample_fn() -> None:
        return None

    tab_config = maker.get_fire_tab_using_fire(
        func=sample_fn,
        tab_weight=2,
        start_dir="/work/app",
        fire_flags="--trace",
    )

    assert tab_config == {
        "command": "/config/scripts/wrap_mcfg fire --trace work/tool.py sample_fn ",
        "startDir": "/work/app",
        "tabName": "sample_fn",
        "tabWeight": 2,
    }


def test_make_layout_from_functions_uses_script_builder_and_appends_tabs() -> None:
    def one() -> None:
        return None

    def two() -> None:
        return None

    def fake_get_fire_tab_using_uv(
        func: Callable[[], object],
        tab_weight: int,
        import_module: bool,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        start_dir: str,
        uv_run_flags: str,
    ) -> tuple[TabConfig, Path]:
        assert import_module is False
        assert uv_with == ["rich"]
        assert uv_project_dir == "/work/app"
        assert uv_run_flags == "--quiet"
        return (
            {
                "command": f"uv run {func.__name__}.py",
                "startDir": start_dir,
                "tabName": func.__name__,
                "tabWeight": tab_weight,
            },
            Path(f"/tmp/{func.__name__}.py"),
        )

    maker.get_fire_tab_using_uv = fake_get_fire_tab_using_uv

    layout = maker.make_layout_from_functions(
        functions=[one, two],
        functions_weights=[2, 5],
        import_module=False,
        tab_configs=[{"tabName": "tail", "startDir": "/logs", "command": "tail -f logs"}],
        layout_name="demo",
        method="script",
        uv_with=["rich"],
        uv_project_dir="/work/app",
        flags="--quiet",
        start_dir="/work/app",
    )

    assert layout == {
        "layoutName": "demo",
        "layoutTabs": [
            {
                "command": "uv run one.py",
                "startDir": "/work/app",
                "tabName": "one",
                "tabWeight": 2,
            },
            {
                "command": "uv run two.py",
                "startDir": "/work/app",
                "tabName": "two",
                "tabWeight": 5,
            },
            {
                "tabName": "tail",
                "startDir": "/logs",
                "command": "tail -f logs",
            },
        ],
    }


def test_make_layout_from_functions_uses_fire_builder_when_requested() -> None:
    def sample_fn() -> None:
        return None

    def fake_get_fire_tab_using_fire(
        func: Callable[[], object],
        tab_weight: int,
        start_dir: str,
        fire_flags: str,
    ) -> TabConfig:
        return {
            "command": f"fire {func.__name__} {fire_flags}",
            "startDir": start_dir,
            "tabName": func.__name__,
            "tabWeight": tab_weight,
        }

    maker.get_fire_tab_using_fire = fake_get_fire_tab_using_fire

    layout = maker.make_layout_from_functions(
        functions=[sample_fn],
        functions_weights=None,
        import_module=True,
        tab_configs=[],
        layout_name="demo",
        method="fire",
        uv_with=None,
        uv_project_dir=None,
        flags="--trace",
        start_dir="/work/app",
    )

    assert layout == {
        "layoutName": "demo",
        "layoutTabs": [
            {
                "command": "fire sample_fn --trace",
                "startDir": "/work/app",
                "tabName": "sample_fn",
                "tabWeight": 1,
            }
        ],
    }
