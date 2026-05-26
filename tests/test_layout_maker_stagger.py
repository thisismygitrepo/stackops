import base64
from pathlib import Path
from types import FunctionType

from stackops.cluster.sessions_managers.utils import maker
from stackops.utils.schemas.layouts.layout_types import TabConfig


def worker() -> None:
    pass


def test_make_layout_from_functions_staggers_generated_tab_commands(monkeypatch) -> None:
    def fake_get_fire_tab_using_uv(
        func: FunctionType,
        tab_weight: int,
        import_module: bool,
        uv_with: list[str] | None,
        uv_project_dir: str | None,
        start_dir: str,
        uv_run_flags: str,
    ) -> tuple[TabConfig, Path]:
        return {
            "command": "echo generated",
            "startDir": start_dir,
            "tabName": func.__name__,
            "tabWeight": tab_weight,
        }, Path("worker.py")

    extra_tab: TabConfig = {
        "command": "echo extra",
        "startDir": "~",
        "tabName": "extra",
    }
    monkeypatch.setattr(maker, "get_fire_tab_using_uv", fake_get_fire_tab_using_uv)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("random.uniform", lambda minimum, maximum: 1.25)

    layout = maker.make_layout_from_functions(
        functions=[worker],
        functions_weights=None,
        import_module=True,
        tab_configs=[extra_tab],
        layout_name="staggered",
        method="script",
        uv_with=None,
        uv_project_dir=None,
        flags="",
        start_dir="~",
        max_stagger=5.0,
    )

    assert layout["layoutTabs"][0]["command"] == "bash -lc 'sleep 1.250000; echo generated'"
    assert layout["layoutTabs"][1] is extra_tab
    assert extra_tab["command"] == "echo extra"


def test_windows_stagger_uses_encoded_powershell_command(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")
    monkeypatch.setattr("random.uniform", lambda minimum, maximum: 1.25)

    command = maker._prepend_random_stagger("echo generated", max_stagger=5.0)
    encoded_script = command.rsplit(" ", maxsplit=1)[1]
    ps_script = base64.b64decode(encoded_script).decode("utf-16-le")

    assert command.startswith("powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand ")
    assert ps_script == "Start-Sleep -Milliseconds 1250\necho generated"


def test_stagger_rejects_negative_values() -> None:
    try:
        maker._prepend_random_stagger("echo generated", max_stagger=-1.0)
    except ValueError as error:
        assert str(error) == "max_stagger must be greater than or equal to 0"
    else:
        raise AssertionError("Expected negative max_stagger to raise ValueError")
