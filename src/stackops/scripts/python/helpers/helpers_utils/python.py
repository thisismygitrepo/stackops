from pathlib import Path
from typing import Annotated, Literal

import typer

ENV_SUMMARY_LIMIT = 96


def _truncate_text(text: str, limit: int) -> tuple[str, int]:
    length = len(text)
    if length <= limit:
        return text, 0
    return text[:limit], length - limit


def _format_env_label(env_key: str, env_value: str) -> str:
    sanitized_value = env_value.replace("\n", "\\n").replace("\t", "\\t")
    preview, remainder = _truncate_text(sanitized_value, ENV_SUMMARY_LIMIT)
    summary = preview if preview else "<empty>"
    if remainder > 0:
        summary = f"{summary}... (+{remainder} chars)"
    return f"{env_key} = {summary}"


def _format_env_preview(env_key: str, env_value: str) -> str:
    value_text = env_value if env_value else "<empty>"
    return f"{env_key}\n\n{value_text}"


def _format_path_preview(path_entry: str) -> str:
    from stackops.scripts.python.helpers.helpers_env.path_manager_backend import get_directory_contents

    path_obj = Path(path_entry)
    if path_obj.exists():
        entry_type = "directory" if path_obj.is_dir() else "file"
    else:
        entry_type = "missing"
    content_lines = get_directory_contents(path_entry, max_items=30)
    contents = "\n".join(content_lines)
    return (
        f"{path_entry}\n\n"
        f"Exists: {path_obj.exists()}\n"
        f"Type: {entry_type}\n\n"
        f"{contents}"
    )


def _build_env_selection_data() -> tuple[dict[str, str], dict[str, str]]:
    import os

    options_to_preview: dict[str, str] = {}
    options_to_output: dict[str, str] = {}
    for env_key, env_value in sorted(os.environ.items(), key=lambda pair: pair[0].lower()):
        label = _format_env_label(env_key, env_value)
        options_to_preview[label] = _format_env_preview(env_key, env_value)
        options_to_output[label] = env_value
    return options_to_preview, options_to_output


def _build_path_selection_data() -> tuple[dict[str, str], dict[str, str]]:
    from stackops.scripts.python.helpers.helpers_env.path_manager_backend import get_path_entries

    options_to_preview: dict[str, str] = {}
    options_to_output: dict[str, str] = {}
    for idx, path_entry in enumerate(get_path_entries(), start=1):
        path_obj = Path(path_entry)
        status = "OK" if path_obj.exists() else "MISSING"
        label = f"{idx:03d} [{status}] {path_entry}"
        options_to_preview[label] = _format_path_preview(path_entry)
        options_to_output[label] = path_entry
    return options_to_preview, options_to_output


def _choose_with_tv(which: Literal["PATH", "p", "ENV", "e"]) -> tuple[bool, str | None]:
    from stackops.utils.cli_utils.command_lookup import check_tool_exists

    if not check_tool_exists("tv"):
        return False, None

    from stackops.utils.options_utils.tv_options import choose_from_dict_with_preview

    options_to_preview: dict[str, str]
    options_to_output: dict[str, str]
    preview_size_percent: float
    if which in {"PATH", "p"}:
        options_to_preview, options_to_output = _build_path_selection_data()
        preview_size_percent = 60.0
    else:
        options_to_preview, options_to_output = _build_env_selection_data()
        preview_size_percent = 50.0

    selected_label = choose_from_dict_with_preview(
        options_to_preview_mapping=options_to_preview,
        extension="txt",
        multi=False,
        preview_size_percent=preview_size_percent,
    )

    if selected_label is None:
        return True, None
    return True, options_to_output.get(selected_label)


def _run_textual_env(which: Literal["PATH", "p", "ENV", "e"]) -> None:
    from stackops.scripts.python.helpers import helpers_env as navigator
    if which in {"PATH", "p"}:
        path = Path(navigator.__file__).resolve().parent.joinpath(navigator.PATH_MANAGER_TUI_PATH_REFERENCE)
    else:
        path = Path(navigator.__file__).resolve().parent.joinpath(navigator.ENV_MANAGER_TUI_PATH_REFERENCE)
    from stackops.utils.code import run_shell_script, get_uv_command_executing_python_script
    from stackops.utils.ssh_utils.abc import STACKOPS_REQUIREMENT

    uv_with = ["textual"]
    uv_project_dir = None
    if not Path.home().joinpath("code/stackops").exists():
        uv_with.append(STACKOPS_REQUIREMENT)
    else:
        uv_project_dir = str(Path.home().joinpath("code/stackops"))
    run_shell_script(
        get_uv_command_executing_python_script(python_script=path.read_text(encoding="utf-8"), uv_with=uv_with, uv_project_dir=uv_project_dir)[0],
        display_script=True,
        clean_env=False,
    )


def tui_env(which: Annotated[Literal["PATH", "p", "ENV", "e"], typer.Argument(help="Which environment variable to display.")] = "ENV", tui: bool = False) -> None:
    """📚 Navigate PATH and environment variables."""
    if tui:
        _run_textual_env(which=which)
        return

    used_tv, selected_value = _choose_with_tv(which=which)
    if selected_value is not None:
        typer.echo(selected_value)
        return
    if used_tv:
        return

    typer.echo("tv picker unavailable. Falling back to the Textual TUI.", err=True)
    _run_textual_env(which=which)


def edit_file_with_hx(
    path: Annotated[str | None, typer.Argument(..., help="The root directory of the project to edit, or a file path.")] = None,
) -> None:
    from pathlib import Path

    if path is None:
        root_path = Path.cwd()
        print(f"No path provided. Using current working directory: {root_path}")
    else:
        root_path = Path(path).expanduser().resolve()
        print(f"Using provided path: {root_path}")
    from stackops.utils.accessories import get_repo_root

    repo_root = get_repo_root(root_path)
    if repo_root is not None and repo_root.joinpath("pyproject.toml").exists():
        code = f"""
cd {repo_root}
uv add --dev pylsp-mypy python-lsp-server[mypy] pyright ruff-lsp  # for helix editor.
source ./.venv/bin/activate
"""
    else:
        code = ""
    if root_path.is_file():
        code += f"hx {root_path}"
    else:
        code += "hx"
    from stackops.utils.code import exit_then_run_shell_script

    exit_then_run_shell_script(code)


if __name__ == "__main__":
    from stackops.utils.machine.specs import get_machine_specs
    get_machine_specs()
