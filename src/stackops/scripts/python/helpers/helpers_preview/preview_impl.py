"""Pure Python implementation for preview command - no typer dependencies."""

from pathlib import Path
import shutil
# from typing import Optional
from stackops.scripts.python.enums import BACKENDS
from stackops.utils.ssh_utils.abc import STACKOPS_VERSION
from stackops.utils.source_of_truth import STACKOPS_REPO_DIR

PATH_BACKENDS = frozenset(
    {
        "preview",
        "auto",
        "browser",
        "glow",
        "rainfrog",
        "lazysql",
        "dblab",
        "usql",
        "harlequin",
        "sqlit",
    }
)
DATABASE_BACKENDS = frozenset({"rainfrog", "lazysql", "dblab", "usql", "harlequin", "sqlit"})
STACKOPS_PLOT_REQUIREMENT = f"stackops[plot]>={STACKOPS_VERSION}"
INTERACITIVITY_FLAG = "-i"


def preview(
    path: str,
    project_path: str | None,
    uv_with: str | None,
    backend: BACKENDS,
    profile: str | None,
    frozen: bool,
) -> None:
    """Preview files and launch reader backends."""
    uv_with_line_user: str = "INVALID_INIT_VALUE_FOR_UV_WITH"
    if frozen:
        uv_with_line_user += " --frozen"
        if uv_with is not None:
            raise RuntimeError("Frozen flag contradicts uv_with, you can't have both at the same time.")
    else:
        if uv_with is not None:
            match backend:
                case "ipython":
                    uv_with_line_user = f"--with {uv_with},ipython,rich"
                case _:
                    uv_with_line_user = f"--with {uv_with}"
        else:
            match backend:
                case "ipython":
                    uv_with_line_user = "--with ipython,rich"
                case _:
                    uv_with_line_user = ""


    from stackops.scripts.python.helpers.helpers_preview.preview_read import get_read_python_file_pycode
    from stackops.utils.meta import lambda_to_python_script
    from stackops.utils.accessories import randstr
    import json
    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    ipython_profile: str | None = profile
    from stackops.scripts.python.helpers.helpers_utils.path_helper import get_choice_file
    if backend in PATH_BACKENDS:
        choice_file = _resolve_path_backend_target(path=path)
        _run_path_backend(
            target_path=choice_file,
            backend=backend,
        )
        return
    if Path(path).absolute().expanduser().is_dir():
        program = ""
        choice_file = Path(path).absolute().expanduser()
    else:
        choice_file = get_choice_file(path=path, suffixes={".*"}, search_root=None)
        if choice_file.suffix == ".py":
            program = choice_file.read_text(encoding="utf-8")
            text = f"📄 Selected file: {choice_file.name}"
            console.print(Panel(text, title="[bold blue]Info[/bold blue]"))
        else:
            from stackops.utils.files import read as read_module
            suffix = choice_file.suffix[1:]
            if suffix == "":
                program = """print('''No file extension found. Cannot determine how to read the file.''')"""
            else:
                reader = read_module.READERS.get(suffix)
                if reader is None:
                    program = f"""print('''No reader found for files with the .{suffix} extension in file `{choice_file}`.''')"""
                else:
                    reader_name = getattr(reader, "__name__", type(reader).__name__)
                    program = Path(read_module.__file__).read_text(encoding="utf-8")
                    program += f"""
# p = {reader_name}("{str(choice_file)}")
from rich.panel import Panel
from rich.console import Console
from stackops.scripts.python.helpers.helpers_preview.preview_read import print_data_preview
from pathlib import Path
console = Console()
p = Path(rf"{choice_file}").absolute()
try:
    dat = read_file(p)
    print_data_preview(console=console, path=p, dat=dat)
except Exception as e:
    error_message = f'''❌ ERROR READING FILE\nFile: {{p.name}}\nError: {{e}}'''
    from rich.text import Text
    console.print(Panel(Text(error_message, justify="left"), title="Error", expand=False, border_style="red"))
    """
            text = f"📄 Reading data from: {choice_file.name}"
            console.print(Panel(text, title="[bold blue]Info[/bold blue]"))


    preprogram = _build_preprogram()
    pyfile = Path.home().joinpath(f"tmp_results/tmp_scripts/python/preview/{randstr()}/script.py")
    pyfile.parent.mkdir(parents=True, exist_ok=True)
    title = "Reading Data"
    def_code = lambda_to_python_script(
        lambda: get_read_python_file_pycode(path=str(pyfile), title=title),
        in_global=False, import_module=False
    )
    python_program = preprogram + "\n\n" + def_code + program
    pyfile.write_text(python_program, encoding="utf-8")
    ipython_profile = ipython_profile if ipython_profile is not None else "default"

    nb_target = pyfile.with_suffix(".ipynb")
    if backend == "jupyter":
        try:
            nb_path = pyfile.with_suffix(".ipynb")
            nb_content = {
                "cells": [
                    {
                        "cell_type": "code",
                        "metadata": {"language": "python"},
                        "source": [python_program],
                        "outputs": [],
                        "execution_count": None,
                    }
                ],
                "metadata": {},
                "nbformat": 4,
                "nbformat_minor": 5,
            }
            nb_path.write_text(json.dumps(nb_content), encoding="utf-8")
            nb_target = nb_path
        except Exception:
            pass


    if project_path is not None:
        uv_project_line = f'--project {project_path}'
        uv_python_line = ""
    else:

        # from stackops.scripts.python.helpers.helpers_utils.python_env import find_virtualenv_root
        # virtualenv_root = find_virtualenv_root(choice_file)

        # if virtualenv_root is not None:
        #     uv_project_line = f'--project {virtualenv_root.parent}'
        #     uv_python_line = ""
        # else:
        if STACKOPS_REPO_DIR.exists():
            uv_project_line = f"""--project "{str(STACKOPS_REPO_DIR)}" --with cowsay --with "{STACKOPS_PLOT_REQUIREMENT}" """
            uv_python_line = "--python 3.14"
        else:
            uv_project_line = f"""--with "{STACKOPS_PLOT_REQUIREMENT}" """
            uv_python_line = "--python 3.14"

    fire_line = build_read_command(
        file_obj=choice_file,
        pyfile=pyfile,
        nb_target=nb_target,
        backend=backend,
        ipython_profile=ipython_profile,
        uv_python_line=uv_python_line,
        uv_project_line=uv_project_line,
        user_uv_with_line=uv_with_line_user,
        uv_with=uv_with,
    )

    from stackops.utils.code import exit_then_run_shell_script
    exit_then_run_shell_script(fire_line, strict=False)


def _resolve_path_backend_target(path: str) -> Path:
    from stackops.scripts.python.helpers.helpers_utils.path_helper import get_choice_file, sanitize_path

    if Path(path).expanduser().exists():
        return sanitize_path(path)
    return get_choice_file(path=path, suffixes={".*"}, search_root=None)


def _run_path_backend(
    target_path: Path,
    backend: BACKENDS,
) -> None:
    """Run the file preview/viewer flows directly from preview."""
    match backend:
        case "preview":
            from stackops.settings.yazi.scripts.fullscreen_preview import preview_target

            terminal_columns = shutil.get_terminal_size(fallback=(120, 40)).columns
            exit_code = preview_target(target_path=target_path, terminal_columns=terminal_columns)
            if exit_code != 0:
                raise SystemExit(exit_code)
        case "auto":
            from stackops.settings.yazi.scripts.interactive_view import build_command, exec_command

            command = build_command(target_path=target_path)
            exec_command(command)
        case "browser":
            from stackops.settings.yazi.scripts.interactive_view import build_command, exec_command

            command = build_command(target_path=target_path, mode="browser")
            exec_command(command)
        case "glow":
            from stackops.settings.yazi.scripts.interactive_view import build_command, exec_command

            command = build_command(target_path=target_path, mode="markdown")
            exec_command(command)
        case _ if backend in DATABASE_BACKENDS:
            from stackops.settings.yazi.scripts.interactive_view import build_command, exec_command

            command = build_command(
                target_path=target_path,
                mode="database",
                database_backend=backend,
            )
            exec_command(command)
        case _:
            raise ValueError(f"Unsupported path backend: {backend}")


def _build_preprogram() -> str:
    """Build the preprogram code for preview."""
    import inspect
    import textwrap
    from typing import Callable

    def get_body_simple_function_no_args(f: Callable[[], None]) -> str:
        return textwrap.dedent("\n".join(inspect.getsource(f).splitlines()[1:]))

    preprogram = """
#%%
"""

    def preprogram_func() -> None:
        try:
            from stackops.utils.files.headers import print_header, print_logo
            print_header()
            print_logo("StackOps")
        except ImportError:
            print("Preview: stackops is not installed in the current environment.")
    preprogram += get_body_simple_function_no_args(preprogram_func)
    return preprogram


def build_read_command(
    file_obj: Path,
    pyfile: Path,
    nb_target: Path,
    backend: BACKENDS,
    ipython_profile: str,
    uv_python_line: str,
    uv_project_line: str,
    user_uv_with_line: str,
    uv_with: str | None,
) -> str:
    """Build the fire line command for preview."""
    if backend == "visidata":
        if file_obj.suffix == ".json":
            return f"""uv run {uv_python_line} {user_uv_with_line} {uv_project_line} --with visidata vd "{str(file_obj)}" """
        return f"""uv run {uv_python_line} {user_uv_with_line} {uv_project_line} --with visidata,pyarrow,openpyxl vd "{str(file_obj)}" """

    if backend == "marimo":
        if STACKOPS_REPO_DIR.exists():
            requirements = f"""{user_uv_with_line} {uv_project_line} --with marimo,sqlglot  """
        else:
            requirements = f"""{uv_python_line} {user_uv_with_line} {uv_project_line} --with "marimo,sqlglot,cowsay,{STACKOPS_PLOT_REQUIREMENT}" """
        return f"""
cd "{str(pyfile.parent)}"
uv run {uv_python_line} --with "marimo" marimo convert {pyfile.name} -o marimo_nb.py
uv run {requirements} marimo edit --host 0.0.0.0 marimo_nb.py
"""

    if backend == "jupyter":
        if STACKOPS_REPO_DIR.exists():
            requirements = f"""{user_uv_with_line}  {uv_project_line} --with jupyterlab """
        else:
            requirements = f"""{user_uv_with_line} {uv_project_line} --with "cowsay" --with "{STACKOPS_PLOT_REQUIREMENT}" """
        return f"uv run {requirements} jupyter-lab {str(nb_target)}"

    if backend == "vscode":
        user_uv_add = f"uv add {uv_with}" if uv_with is not None else ""
        return f"""
cd "{str(pyfile.parent)}"
uv init {uv_python_line}
uv venv
uv add "cowsay" "{STACKOPS_PLOT_REQUIREMENT}"
{user_uv_add}
code --new-window "{str(pyfile)}"
"""

    # It must be that we are reading with Python or IPython:
    if backend == "python":
        interpreter = "python"
        profile = ""
    else:
        interpreter = "python -m IPython"
        profile = f" --profile {ipython_profile} --no-banner"
    ve_line = f"""{uv_python_line} {user_uv_with_line} {uv_project_line} """
    return f"uv run {ve_line} {interpreter} {INTERACITIVITY_FLAG} {profile} {str(pyfile)}"
