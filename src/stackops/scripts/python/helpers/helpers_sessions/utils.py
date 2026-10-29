from pathlib import Path
from typing import Literal


def balance_load(
    layout_path: str,
    max_thresh: int,
    thresh_type: Literal["number", "n", "weight", "w"],
    breaking_method: Literal["moreLayouts", "ml", "combineTabs", "ct"],
    output_path: str | None,
) -> None:
    """Adjust layout file to limit max tabs per layout, etc."""
    thresh_type_resolved: dict[str, Literal["number", "weight"]] = {"number": "number", "n": "number", "weight": "weight", "w": "weight"}
    breaking_method_resolved: dict[str, Literal["moreLayouts", "combineTabs"]] = {
        "moreLayouts": "moreLayouts",
        "ml": "moreLayouts",
        "combineTabs": "combineTabs",
        "ct": "combineTabs",
    }
    try:
        resolved_thresh_type = thresh_type_resolved[thresh_type]
        resolved_breaking_method = breaking_method_resolved[breaking_method]
    except KeyError as error:
        raise ValueError(f"Unsupported balance-load option: {error.args[0]}.") from error

    layout_path_obj = Path(layout_path).expanduser().absolute()
    if not layout_path_obj.exists():
        raise ValueError(f"Layout file not found: {layout_path_obj}")
    if not layout_path_obj.is_file():
        raise ValueError(f"Layout path is not a file: {layout_path_obj}")

    from stackops.utils.schemas.layouts.layout_constants import LAYOUT_FILE_SUFFIX
    from stackops.utils.schemas.layouts.layout_file import read_layouts_file, write_layouts_file
    from stackops.cluster.sessions_managers.utils.load_balancer import limit_tab_num

    layoutfile = read_layouts_file(path=layout_path_obj)
    new_layouts = limit_tab_num(
        layout_configs=layoutfile["layouts"],
        max_thresh=max_thresh,
        threshold_type=resolved_thresh_type,
        breaking_method=resolved_breaking_method,
    )
    layoutfile["layouts"] = new_layouts
    target_file = (
        Path(output_path).expanduser().absolute()
        if output_path is not None
        else layout_path_obj.parent / f"{layout_path_obj.stem}_adjusted_{max_thresh}_{thresh_type}_{breaking_method}{LAYOUT_FILE_SUFFIX}"
    )
    write_layouts_file(path=target_file, layouts_file=layoutfile)
    print(f"Adjusted layout saved to {target_file}")


def create_template(name: str | None, num_tabs: int) -> None:
    """Create a layout template file."""
    from stackops.utils.schemas.layouts.layout_constants import LAYOUT_FILE_SUFFIX, LAYOUT_FILE_VERSION
    from stackops.utils.schemas.layouts.layout_file import write_layouts_file
    from stackops.utils.schemas.layouts.layout_types import LayoutsFile, TabConfig, LayoutConfig, single_pane_tab

    tabs: list[TabConfig] = []
    import platform

    if platform.system().lower() == "windows":
        default_command = "powershell"
    else:
        default_command = "bash"
    current_directory = Path.cwd()
    home_directory = Path.home()
    start_directory = (
        f"""~/{current_directory.relative_to(home_directory).as_posix()}"""
        if current_directory.is_relative_to(home_directory)
        else str(current_directory)
    )
    for i in range(1, num_tabs + 1):
        tabs.append(single_pane_tab(tab_name=f"Tab{i}", start_dir=start_directory, command=default_command))
    layouts: list[LayoutConfig] = [{"layoutName": f"{Path.cwd().name}Layout", "layoutTabs": tabs}]
    file: LayoutsFile = {"version": LAYOUT_FILE_VERSION, "layouts": layouts}
    layout_stem = "layout" if name is None else name.removesuffix(LAYOUT_FILE_SUFFIX)
    layout_path = Path.cwd() / f"{layout_stem}{LAYOUT_FILE_SUFFIX}"
    if layout_path.exists():
        print(f"❌ File {layout_path} already exists. Aborting to avoid overwriting.")
        return
    write_layouts_file(path=layout_path, layouts_file=file)
    print(f"✅ Created layout template at {layout_path}")
