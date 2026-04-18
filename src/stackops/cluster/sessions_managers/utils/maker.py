
from types import FunctionType
from typing import Literal
from stackops.utils.schemas.layouts.layout_types import TabConfig, LayoutConfig
from pathlib import Path

def get_fire_tab_using_uv(func: FunctionType, tab_weight: int, import_module: bool, uv_with: list[str] | None, uv_project_dir: str | None, start_dir: str, uv_run_flags: str) -> tuple[TabConfig, Path]:
    from stackops.utils.meta import lambda_to_python_script
    if func.__name__ == "<lambda>":
        py_script =  lambda_to_python_script(func,
                                             in_global=True, import_module=import_module)
    else:
        py_script =  lambda_to_python_script(lambda: func(),
                                             in_global=True, import_module=import_module)
    from stackops.utils.code import get_uv_command_executing_python_script
    command_to_run, py_script_path = get_uv_command_executing_python_script(python_script=py_script, uv_with=uv_with, uv_project_dir=uv_project_dir, uv_run_flags=uv_run_flags)
    tab_config: TabConfig = {
        "command": command_to_run,
        "startDir": start_dir,
        "tabName": func.__name__,
        "tabWeight": tab_weight
    }
    return tab_config, py_script_path
def get_fire_tab_using_fire(func: FunctionType, tab_weight: int, start_dir: str, fire_flags: str) -> TabConfig:
    import inspect
    from stackops.utils.source_of_truth import CONFIG_ROOT
    import platform
    wrap_mcfg: str
    if platform.system().lower() == "windows":
        wrap_mcfg = f'& "{CONFIG_ROOT / "scripts/wrap_mcfg.ps1"}"'
    elif platform.system().lower() == "linux" or platform.system().lower() == "darwin":
        wrap_mcfg = str(CONFIG_ROOT / "scripts/wrap_mcfg")
    else:
        raise ValueError(f"Unsupported platform: {platform.system()}")
    path = Path(inspect.getfile(func))
    path_relative = path.relative_to(Path.home())
    command_to_run = f"""{wrap_mcfg} fire {fire_flags} {path_relative} {func.__name__} """
    tab_config: TabConfig = {
        "command": command_to_run,
        "startDir": start_dir,
        "tabName": func.__name__,
        "tabWeight": tab_weight
    }
    return tab_config



def make_layout_from_functions(functions: list[FunctionType], functions_weights: list[int] | None,
                               import_module: bool, tab_configs: list[TabConfig],
                               layout_name: str, method: Literal["script", "fire"],
                               uv_with: list[str] | None, uv_project_dir: str | None,
                               flags: str,
                               start_dir: str
                               ) -> LayoutConfig:
    tabs2artifacts: list[tuple[TabConfig, list[Path]]] = []
    for a_func, tab_weight in zip(functions, functions_weights or [1]*len(functions)):
        if method == "script":
            tab_config, artifact_file = get_fire_tab_using_uv(
                a_func,
                tab_weight=tab_weight,
                import_module=import_module,
                uv_with=uv_with,
                uv_project_dir=uv_project_dir,
                start_dir=start_dir,
                uv_run_flags=flags
            )
            artifact_files = [artifact_file]
        else:
            tab_config = get_fire_tab_using_fire(a_func, tab_weight=tab_weight, start_dir=start_dir, fire_flags=flags)
            artifact_files = []
        tabs2artifacts.append((tab_config, artifact_files))
    list_of_tabs = [tab for tab, _ in tabs2artifacts] + tab_configs
    layout_config: LayoutConfig = {
        "layoutName": layout_name,
        "layoutTabs": list_of_tabs,
    }
    return layout_config
