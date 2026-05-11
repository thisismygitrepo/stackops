import shlex
from pathlib import Path
from platform import system


def is_windows_host() -> bool:
    return system() == "Windows"


def _resolve_is_windows(*, is_windows: bool | None) -> bool:
    if is_windows is None:
        return is_windows_host()
    return is_windows


def quote_for_shell(value: str, *, is_windows: bool) -> str:
    if is_windows:
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def _render_executable(*, executable: str, is_windows: bool) -> str:
    if " " in executable:
        quoted_executable = quote_for_shell(executable, is_windows=is_windows)
        if is_windows:
            return f"& {quoted_executable}"
        return quoted_executable
    return executable


def build_shell_invocation(*, executable: str, arguments: list[str], is_windows: bool | None = None) -> str:
    resolved_is_windows = _resolve_is_windows(is_windows=is_windows)
    rendered_executable = _render_executable(executable=executable, is_windows=resolved_is_windows)
    if len(arguments) == 0:
        return rendered_executable
    rendered_arguments = " ".join(
        quote_for_shell(argument, is_windows=resolved_is_windows) for argument in arguments
    )
    return f"{rendered_executable} {rendered_arguments}"


def get_agent_command_filename(*, idx: int | str, is_windows: bool | None = None) -> str:
    extension = "ps1" if _resolve_is_windows(is_windows=is_windows) else "sh"
    return f"agent_{idx}_cmd.{extension}"


def get_agent_launcher_glob(*, is_windows: bool | None = None) -> str:
    extension = "ps1" if _resolve_is_windows(is_windows=is_windows) else "sh"
    return f"*_cmd.{extension}"


def get_recreate_script_filename(*, is_windows: bool | None = None) -> str:
    extension = "ps1" if _resolve_is_windows(is_windows=is_windows) else "sh"
    return f"recreate_layout.{extension}"


def get_script_runner_command(*, script_path: Path, is_windows: bool | None = None) -> str:
    resolved_is_windows = _resolve_is_windows(is_windows=is_windows)
    if resolved_is_windows:
        return build_shell_invocation(
            executable="pwsh",
            arguments=["-File", str(script_path)],
            is_windows=True,
        )
    return build_shell_invocation(
        executable="bash",
        arguments=[str(script_path)],
        is_windows=False,
    )


def render_env_assignment(*, name: str, value: str, is_windows: bool) -> str:
    quoted_value = quote_for_shell(value, is_windows=is_windows)
    if is_windows:
        return f"$env:{name} = {quoted_value}"
    return f"export {name}={quoted_value}"


def render_output(*, message: str, is_windows: bool) -> str:
    quoted_message = quote_for_shell(message, is_windows=is_windows)
    if is_windows:
        return f"Write-Output {quoted_message}"
    return f"echo {quoted_message}"


def render_sleep_seconds(*, seconds: float, is_windows: bool) -> str:
    if is_windows:
        return f"Start-Sleep -Seconds {seconds:.2f}"
    return f"sleep {seconds:.2f}"


def render_sleep_milliseconds(*, milliseconds: int, is_windows: bool) -> str:
    if is_windows:
        return f"Start-Sleep -Milliseconds {milliseconds}"
    return f"sleep {milliseconds / 1000:g}"