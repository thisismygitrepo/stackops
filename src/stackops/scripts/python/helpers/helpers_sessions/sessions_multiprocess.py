

from typing import Annotated
import typer


def create_from_function(
        num_process: Annotated[int, typer.Option(..., "--num-process", "-n", help="Number of parallel processes to run")],
        path: Annotated[str, typer.Option(..., "--path", "-p", help="Path to a Python or Shell script file or a directory containing such files")] = ".",
        function: Annotated[str | None, typer.Option(..., "--function", "-f", help="Function to run from the Python file. If not provided, you will be prompted to choose.")] = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_utils.python_env import find_virtualenv_root
    from stackops.utils.options_utils.options import choose_from_options
    from stackops.scripts.python.helpers.helpers_utils.path_helper import match_file_name, sanitize_path
    from stackops.utils.accessories import get_repo_root
    from pathlib import Path

    path_obj = sanitize_path(path)
    if not path_obj.is_file() or function is None or not function.strip():
        from stackops.utils.cli_utils.interaction import is_interactive, require_interactive

        if not is_interactive() and path_obj.is_file() and path_obj.suffix == ".py":
            import ast

            try:
                module = ast.parse(path_obj.read_text(encoding="utf-8"), filename=str(path_obj))
            except (OSError, SyntaxError) as error:
                raise typer.BadParameter(f"Could not inspect script functions: {error}") from error
            names = [node.name for node in module.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
            raise typer.BadParameter(f"--function is required without an interactive terminal. Available callables: {', '.join(names) or '(none)'}. ")
        require_interactive("Choosing a script/function; supply an exact --path FILE and --function NAME")
    if not path_obj.exists():
        suffixes = {".py"}
        choice_file = match_file_name(sub_string=path, search_root=Path.cwd(), suffixes=suffixes)
    elif path_obj.is_dir():
        from stackops.scripts.python.helpers.helpers_utils.path_helper import search_for_files_of_interest
        print(f"🔍 Searching recursively for Python, PowerShell and Shell scripts in directory `{path_obj}`")
        files = search_for_files_of_interest(path_obj, suffixes={".py", ".sh", ".ps1"})
        print(f"🔍 Got #{len(files)} results.")
        selected_file = choose_from_options(multi=False, options=files, tv=True, msg="Choose one option")
        if selected_file is None:
            print("❓ Selection cancelled.")
            raise typer.Exit(code=1)
        choice_file = Path(selected_file)
    else:
        choice_file = path_obj


    repo_root = get_repo_root(Path(choice_file))
    print(f"💾 Selected file: {choice_file}.\nRepo root: {repo_root}")
    virtualenv_root = find_virtualenv_root(choice_file)
    if virtualenv_root is not None:
        start_dir = virtualenv_root.parent
    else:
        start_dir = Path.cwd()

    # =========================  choosing function to run
    if function is None or function.strip() == "":
        from stackops.scripts.python.helpers.helpers_fire_command.fire_jobs_route_helper import choose_function_or_lines
        choice_function, choice_file, _kwargs_dict = choose_function_or_lines(choice_file, kwargs_dict={})
    else:
        choice_function = function

    from stackops.cluster.sessions_managers.tmux.tmux_local import run_tmux_layout
    from stackops.utils.schemas.layouts.layout_types import LayoutConfig, single_pane_tab
    layout: LayoutConfig = {"layoutName": "fireNprocess", "layoutTabs": []}
    for an_arg in range(num_process):
        layout["layoutTabs"].append(single_pane_tab(
            tab_name=f"tab{an_arg}",
            start_dir=str(start_dir),
            command=f"uv run python -m fire {choice_file} {choice_function} --idx={an_arg} --idx_max={num_process}",
        ))
    print(layout)
    run_tmux_layout(layout_config=layout, on_conflict="error")
